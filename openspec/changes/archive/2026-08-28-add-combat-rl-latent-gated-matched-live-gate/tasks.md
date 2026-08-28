## 1. Candidate Runtime

- [x] 1.1 Add RED tests for candidate-mode registration, source/artifact binding, eval-only preconditions, and shadow/candidate mutual exclusion.
- [x] 1.2 Add RED tests for gate-open takeover, gate-closed parent retention, illegal/parity failure, transient waits, final guarded-action evidence, and reset behavior.
- [x] 1.3 Implement the minimal candidate runtime and RL v2 routing before existing outer guards while preserving shadow-only behavior.
- [x] 1.4 Expose the candidate registration through `run_training_batch.py`, clear ambient latent variables by default, and cover child-environment isolation.

## 2. Source Qualification

- [x] 2.1 Run focused candidate, shadow, RL transition, wrapper, and gameplay-profile tests plus strict OpenSpec validation.
- [x] 2.2 Run the qualified commit gate once, record the unchanged raw-full baseline boundary, review the source diff, and commit/push the implementation.

## 3. Matched Gate Registration

- [x] 3.1 Generate and freeze ten fresh seeds, a source-bound candidate registration, candidate/parent launch configs, production restore config, and fixed qualification rules.
- [x] 3.2 Validate hashes, clean tracked source state, absent output boundaries, active r16 identity, and candidate callability before starting gameplay.

## 4. Live Execution And Decision

- [x] 4.1 Run the candidate arm for exactly ten completed games, preserve trace/log/run evidence, and restore production configuration.
- [x] 4.2 Run the production-r16 parent arm on the identical seed order, preserve evidence, and restore production configuration.
- [x] 4.3 Reconcile paired floors, progression, victories, seeds, candidate takeovers, legal final actions, logs, errors, and configuration restoration against every fixed gate.
- [x] 4.4 Publish the qualification/no-go decision without tuning or automatic promotion; sync and archive the completed change and commit/push tracked evidence.
