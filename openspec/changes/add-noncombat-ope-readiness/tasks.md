## 1. Trajectory And Outcome Contracts

- [x] 1.1 Add red tests for canonical sample loading, deterministic trajectory ordering, duplicate identities, complete terminal outcomes, and mixed or censored trajectory blockers.
- [x] 1.2 Implement versioned trajectory and terminal-outcome contract validation with one outcome record per exact run group.
- [x] 1.3 Verify trajectory counts remain independent from repeated decision-row counts and freeze focused regression coverage.

## 2. Target Policy Manifests

- [x] 2.1 Add red tests for source-hash binding, exact rational normalization, support equality, missing rows, duplicate actions, and unsupported probability mass.
- [x] 2.2 Implement the versioned target-policy manifest parser, validator, and deterministic behavior-identity builder.
- [x] 2.3 Implement the deterministic Current-policy builder with explicit label provenance and fail-closed unmapped rows.

## 3. Exact Weight And Overlap Diagnostics

- [x] 3.1 Add red tests for exact decision ratios, trajectory products, zero target support, finite rendering, ESS, ESS fraction, maximum normalized weight, and category-arm summaries.
- [x] 3.2 Implement exact `Fraction`-backed trajectory weighting and deterministic overlap diagnostics without clipping or row-level outcome replication.
- [x] 3.3 Add identity self-check and minimum-screen blocker tests for trajectory count, nonzero count, ESS, concentration, and primary-outcome variation.

## 4. Deterministic Offline Artifacts

- [x] 4.1 Add red tests for stable JSON/Markdown rendering, source hashes, separate readiness gates, and no policy-value or uplift output.
- [x] 4.2 Implement the offline CLI and transactional artifact replacement for target-manifest generation and readiness auditing.
- [x] 4.3 Add invalid-input recovery tests proving malformed or inconsistent inputs do not partially replace a prior complete artifact set.

## 5. B2 Proof Of Concept

- [ ] 5.1 Generate frozen behavior-identity and deterministic-Current target manifests from the B2 sample allowlist.
- [ ] 5.2 Generate B2 readiness JSON/Markdown artifacts that reconstruct exactly 25 trajectories and 230 decisions while keeping every downstream gate false.
- [ ] 5.3 Independently replay target hashes, trajectory weights, identity invariants, overlap metrics, blockers, and live isolation hashes; record the audit result.

## 6. Verification And Closeout

- [ ] 6.1 Run focused trajectory/target/weight/CLI tests with the Windows development environment and record the result.
- [ ] 6.2 Run the full pytest suite, `openspec validate --all --strict`, and `git diff --check`.
- [ ] 6.3 Confirm CommunicationMod configuration, production checkpoints, run records, and live processes were not changed by the offline workflow.
- [ ] 6.4 Update the change artifacts and durable report with final limitations, residual risks, and the next estimator-validation gate; commit and push coherent milestones.
