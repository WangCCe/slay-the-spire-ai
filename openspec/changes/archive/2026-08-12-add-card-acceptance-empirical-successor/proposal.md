## Why

The consumed cross-fitted successor improved paired floor but retained near-total
greedy `take` concentration (`1,773/1,774` final-window card rewards) and zero
victories, while the completed source-only architecture contract now separates
card acceptance from conditional card choice with disjoint parameters. A fresh,
preregistered empirical successor is needed to test that intervention without
reusing consumed cohorts, checkpoints, or outcomes and without mixing in route,
shop, or event policy changes.

## What Changes

- Add a card-reward-only simulator-learning successor that uses the reviewed
  dual-head policy, held-out cross-fitted residual advantages, separately named
  family and conditional policy terms, and head-local entropy regularization.
- Freeze all non-card-reward decision behavior and initialize both arms from one
  newly registered base ranker state. Train a shared-card-head control and a
  disjoint-two-head candidate under otherwise identical terms so the primary
  empirical contrast is parameter sharing rather than unrelated policy drift.
- Preregister one fresh `512`-seed paired training cohort, one at-most-once
  `128`-pair structural canary, and one untouched at-most-once `512`-seed paired
  holdout. This planning change does not materialize or access those seeds.
- Require new candidate/control source, checkpoint, and configuration identities;
  candidate-disabled default; exact control reproduction; a family-only shadow
  step; anti-concentration gates; deterministic evidence; and an independent
  standard-library verifier.
- Classify holdout evidence with preregistered victory and paired-floor rules.
  A floor-only result is retained as simulator-learning evidence, not policy
  quality; no result grants production loading, gameplay, qualification, or
  promotion authority.
- Split later empirical work into source implementation, a separately authorized
  source-only inventory build, fresh registration, training authorization,
  canary authorization, and holdout authorization. A tracked exact authorization
  MAY be derived from an immutable, externally recorded solo-maintainer standing
  delegation after independent request verification and a fresh authoritative
  revocation check at approval and launch, or from a post-request exact
  external-human approval with the same request, scope, ceiling, provenance, and
  revocation bindings. This change and its requests cannot create or modify
  either human record; proposal approval or an unbound permission statement
  alone starts no seed discovery, cohort materialization, native loading,
  environment construction, training, canary, or holdout.
- Roll back before empirical start by removing only additive uncommitted files or
  cancelling the registered candidate. After any evidence-bearing start,
  rollback preserves the immutable result, keeps the candidate disabled, and
  restores the experiment target to the exact registered control binding and
  verifies the registered production configuration/checkpoint inventory; it
  never tunes, replaces, resumes after canary, or retries the identity.

Success requires source-only contract verification and, for a later authorized
execution, all `128` canary pairs to pass the fixed structural gates before any
holdout access. A policy-quality signal additionally requires a complete frozen
`512`-pair holdout, strictly more candidate than control victories, and a
positive preregistered paired-floor lower confidence bound. Mechanism completion,
training floor, entropy, gradient geometry, or canary passage alone is not
success.

## Capabilities

### New Capabilities

- `noncombat-card-acceptance-empirical-successor`: Defines the isolated
  dual-head candidate and matched shared-head control, card-reward training
  objective, deterministic initialization, frozen non-card behavior, fresh
  paired cohort lifecycle, structural canary, paired holdout classification,
  rollback, publication, and authority boundaries.

### Modified Capabilities

None.

## Impact

The implementation will add new `analysis_scripts` control-plane, runtime,
seed-inventory, and independent-verifier modules plus focused tests and bounded
reports. It will reuse only reviewed public policy, objective, formal-reward,
state-projection, simulator-adapter, and cross-fitted attribution APIs under new
source bindings. Consumed runners, registrations, authorizations, checkpoints,
reports, seed inventories, production checkpoints, CommunicationMod
configuration, and live gameplay behavior remain unchanged.
