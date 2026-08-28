## 1. Candidate Contracts And RED Evidence

- [x] 1.1 Add RED tests for exact candidate registration, source/artifact/corpus/parent/device/safety-policy binding, eval-only preconditions, and all-runtime mutual exclusion.
- [x] 1.2 Add RED tests for eligible late takeover, abstention, legality failure, fixed safety veto, runtime fail-closed behavior, transient waits, and complete parent/guard/candidate/selected/final evidence.
- [x] 1.3 Add RED batch-wrapper tests proving explicit candidate propagation and ambient candidate removal for ordinary parent arms.

## 2. Candidate Runtime And Safety Boundary

- [x] 2.1 Implement the source-bound CPU action-relative candidate registration and runtime without changing historical shadow schemas.
- [x] 2.2 Add RL v2 late-proposal and final-commit routing, preserving the guard action on any runtime or decode failure.
- [x] 2.3 Add the fixed `CombatRLAgent` late-candidate safety veto and record exact veto or takeover provenance before the final action commit.
- [x] 2.4 Add the candidate registration argument and four-runtime environment isolation to `run_training_batch.py`.

## 3. Source Qualification

- [x] 3.1 Run focused candidate, shadow, RL transition, outer-agent, wrapper, and summary tests plus Python compilation and strict OpenSpec validation.
- [x] 3.2 Run one repository commit gate with a timing report, review the scoped source diff, and commit/push the qualified source boundary.

  The qualified source boundary passed 4,327 tests with 26 skipped and 21
  deselected in 165.12 seconds. The 22 candidate-specific tests took 0.68
  seconds; the new runtime is not a material contributor to the full-gate
  duration, which remains below the registered 300-second ceiling.

## 4. Matched Gate Registration

- [x] 4.1 Freeze ten fresh Ironclad A0 seeds, a source-bound candidate registration, candidate/parent launch configs, production restore config, and fixed paired qualification rules.
- [x] 4.2 Validate committed source and registration, artifact/corpus/checkpoint/state identities, clean tracked source, absent output boundaries, active r16 identity, and candidate callability before gameplay.

## 5. Live Execution And Decision

- [x] 5.1 Run the candidate arm for exactly ten completed games, preserve trace/log/run evidence, and restore the exact production configuration.
- [x] 5.2 Run the production-r16 parent arm on the identical seed order, preserve evidence, and restore the exact production configuration.
- [x] 5.3 Reconcile paired floors, progression, victories, seeds, safe takeovers, vetoes, legal final actions, logs, errors, and restoration against every fixed condition.
- [x] 5.4 Publish the qualification/no-go decision without tuning or automatic promotion; sync and archive the completed change and commit/push compact evidence.

  The candidate completed both registered arms and every technical condition,
  but lost two paired floor comparisons, reached 219 total floors versus the
  parent's 229, and entered Act 2 five times versus six. Production r16 remains
  authoritative; this cohort is closed without promotion, tuning, or retry.
