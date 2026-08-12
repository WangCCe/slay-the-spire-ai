## 1. Bound Existing Evidence

- [ ] 1.1 Add a source-bound reader for the archived warm-start train/validation card rows that rejects final-test access and corpus drift.
- [ ] 1.2 Add a Bottled card-label bridge that binds the clean checkout, maps every label to one legal candidate, and reports family/confidence/disagreement counts.
- [ ] 1.3 Add focused regressions for missing context, ambiguous labels, bowl mapping, corpus drift, and final-test denial.

## 2. Hybrid Native-Baseline Rollouts

- [ ] 2.1 Add RED regressions proving candidate non-card and all control decisions use source-preserving native SimpleAgent actions with no learned fallback.
- [ ] 2.2 Implement separate-seed-matched candidate/control rollouts with hierarchical candidate card routing and frozen native control routing.
- [ ] 2.3 Verify source immutability, legal action mapping, terminal outcomes, zero control optimizer state, and native-query failure closure.

## 3. Card-Only Warm Start

- [ ] 3.1 Project mapped train/validation rows through the current state-conditioned card feature bridge and hierarchical family/conditional targets.
- [ ] 3.2 Implement the fixed deterministic supervised schedule and canonical zero-step/final model encoding.
- [ ] 3.3 Implement the one-shot validation gate for mapping, family/exact-action agreement, relative improvement, and 5%-95% take coverage.
- [ ] 3.4 Add deterministic replay, head ownership, no-reward, no-validation-update, and failed-gate-no-RL regressions.

## 4. Candidate-Only Residual Runtime

- [ ] 4.1 Adapt the accelerated four-fold baseline and optimizer step so only candidate card parameters update and native control remains optimizer-free.
- [ ] 4.2 Add the fixed pre-RL source-state probe, complete-boundary checkpoint restore, resource accounting, and 5%-95% concentration stop.
- [ ] 4.3 Add regressions for one complete chunk, invalid gradients/rewards, unsupported episodes, deadline failure, concentration stop, and partial-checkpoint rejection.

## 5. Bounded Pilot And Report

- [ ] 5.1 Publish a compact source/native/Bottled/corpus/config registration and preflight that denies protected cohorts, game processes, CommunicationMod, and production checkpoints.
- [ ] 5.2 Run the warm-start gate once; only on pass, run at most four residual chunks on the consumed development cohort.
- [ ] 5.3 Run one frozen candidate-versus-native-control comparison and publish the strict ready/not-ready verdict with rollback state.

## 6. Verification And Closeout

- [ ] 6.1 Run focused Bottled, adapter, warm-start, hybrid-rollout, residual-runtime, checkpoint, and report tests using the scoped system-temp pytest root.
- [ ] 6.2 Run the repository pytest gate once after focused tests pass; do not launch live gameplay because no live loader or policy changes under this capability.
- [ ] 6.3 Run strict OpenSpec validation, review the final diff and authority flags, then commit and push cohesive implementation/evidence boundaries.
