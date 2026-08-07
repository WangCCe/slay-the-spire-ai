# Cross-Fitted Control-Plane Repair Closeout

Date: 2026-08-07

Status: `source_only_control_plane_repaired_no_empirical_authority`

## Boundary

This change repairs only the cross-fitted successor execution control plane and
its independent standard-library verifier. It did not load native code, access
a registered seed, construct an environment, fit or load a model, train,
evaluate, run OPE, launch gameplay or CommunicationMod, qualify, promote,
resume, replay, authorize a new cohort, or modify the consumed terminal bundle.

## Repair

- One private execution context performs one complete raw registration
  validation, owns a recursively immutable JSON-compatible copy, caches the
  exact digest/identity/output binding, and remains constant through 64 access
  operations and same-process terminal closeout.
- Every post-start terminal path records a final
  `terminal-attempt-charge`. Synthetic failures record 7.5 seconds exactly,
  clamp 14,405 seconds to the 14,400-second ceiling, carry a prior 12-second
  resume charge into a 14,388-second remaining deadline, and publish an
  idempotent no-op witness without changing ledger bytes twice.
- Same-process closeout carries its canonical terminal intent forward while
  still comparing its exact disk bytes. Interrupted publication continues to
  reopen and validate the raw intent and durable inventories.
- The independent verifier holds a dead-owner lease lock across the complete
  evidence read. Its descriptor is bound to the checked path with no-follow
  where available plus `lstat`/`fstat` identity checks. Lease-free archived
  verification requires regular terminal and manifest closeout markers and
  rechecks that no lease appeared before evidence enumeration.
- Operational guidance keeps wrapper completion separate from true Python
  child exit and requires an unlocked, readable lease before active-root
  inspection.

## Independent Review

Read-only `codex-cli 0.144.6` review with `gpt-5.6-terra` confirmed three high
severity findings: mutable nested context values, a lease-free boundary race,
and lease path/handle replacement. All three received focused RED regressions,
narrow fixes, and final source-focused coverage.

Review evidence:

- Initial review RED selection: `3 failed in 6.04s`.
- Refined path-replacement RED: `1 failed in 2.42s`.
- Focused GREEN selection: `3 passed in 1.59s`.
- Final six-file source-focused suite: `193 passed, 1 skipped in 128.04s`.

The repository commit gate ran exactly once and passed 4,434 tests with 17
skips in 657.01 seconds, 659.89 seconds including orchestration. It was not
rerun because of duration.

## Source Bindings

- Producer: 215,724 bytes, SHA-256
  `8e33b5bff22647bb96c7bbdab6c5d0f50181bd08340df66142065de3d4b55a92`.
- Independent verifier: 197,780 bytes, SHA-256
  `ef7054012da2b0ef062f542e94075ff09f5f7f6dc121759fa21fac062b89ba60`.
- Control regressions: 112,778 bytes, SHA-256
  `eec3676c9c60c1e40907c7e34e721422063c9bd28e4b848607300ad3ed30258a`.
- Verifier regressions: 96,223 bytes, SHA-256
  `550850a79d3694b5258b6d0d8abd21ca1e21d6a268e300642ca85b3e22c6494a`.

## Verdict

The known registration-throughput, elapsed-charge, terminal-publication, and
true-child-liveness control-plane defects are repaired at the source boundary.
This does not establish mechanism evidence, policy quality, a causal effect,
target-supported outcomes, formal RL readiness, or gameplay value.

Any empirical successor requires a separately reviewed proposal, new pushed
source identity, fresh registration and cohort decision, exact request, and
separate explicit human approval. This closeout grants none of that authority.

## OpenSpec

The five additive control-plane requirements were synced to the main
`noncombat-cross-fitted-hierarchical-learning-successor` specification. The
completed `spec-driven` change is archived at
`openspec/changes/archive/2026-08-07-repair-cross-fitted-execution-control-plane`.
