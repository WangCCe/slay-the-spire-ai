## Why

The first registered teacher-sufficiency audit failed closed after its timed
body exceeded the fixed 120-second limit, leaving no canonical result. A narrow
runtime recovery is needed to remove redundant pure computation while keeping
the consumed attempt immutable and every evidence, signature, and verdict
definition unchanged.

## What Changes

- Add an equivalence-preserving execution path that loads and validates the
  191 MB train input once, then passes an explicit validated context into the
  timed audit body without deep-copying or recanonicalizing the full dataset.
- Reuse the policy-view SHA-256 values already validated in each demonstration
  row for `adapter-observable-v1`, instead of serializing the same full state for
  every candidate again.
- Compute structured global state features once per decision and copy them into
  each candidate feature map; category-specific route/card features and exact
  float32 hashing remain unchanged.
- Add reference-versus-optimized byte-equivalence regressions, validation/load
  call-count checks, and a generated non-corpus performance fixture before any
  fresh registration.
- Bind the blocked attempt as immutable lineage, create one fresh registration,
  and permit one new canonical execution only if focused, commit-gate,
  equivalence, identity, and synthetic performance checks pass.

No live evidence is collected. The recovery uses no native module, simulator,
model, new seed, outcome, reward, validation/final cohort, or gameplay. Success
requires exact reference/optimized signatures and artifacts on fixtures plus a
fresh registered audit body within the unchanged 120-second limit; it is not a
policy-quality result by itself.

## Capabilities

### New Capabilities

- `noncombat-teacher-sufficiency-audit-runtime-recovery`: Defines immutable
  blocked-attempt lineage, validated single-load execution, exact feature/hash
  equivalence, non-corpus performance proof, fresh registration, and one-shot
  recovery publication.

### Modified Capabilities

None.

## Impact

- Modifies only the offline teacher-sufficiency audit script and focused tests;
  adds one recovery registration and result/failure reports.
- Reads the same train-only gzip, local/external source files, and consumed
  failure record without modifying them.
- Changes no canonical signature, dependency classification, suitability check,
  verdict order, resource limit, native adapter, production agent, live config,
  or formal-RL path. Rollback restores the prior audit script/tests and deletes
  only recovery OpenSpec, registration, and generated recovery artifacts.
