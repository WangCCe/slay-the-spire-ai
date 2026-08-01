## Why

R7 is permanently retired after failing at `source_validation_failed`, but the
failure is now reproduced, fixed, regression-covered, and archived as
`fix-qualification-source-byte-normalization`. The v2 known-propensity study
still cannot reach `start` without one new independently verified no-action
qualification, so a separately reviewed r8 identity is the next bounded gate
on the non-combat RL go/no-go path.

## What Changes

- Freeze one previously absent r8 qualification identity while preserving r1
  through r7 and the registered study root exactly as historical evidence.
- Reuse the reviewed v3 bootstrap, request-bound isolation, no-action child,
  standalone verifier, and restoration contracts. R8 adds no runtime feature
  and permits no source repair inside the qualification amendment.
- Require an offline candidate and go/no-go record that bind a clean source
  snapshot, the archived source fix, exact request and runner bytes, inert
  direct-child review paths, CommunicationMod rollback bytes, protected live
  inventories, and uniformly false study and training authority.
- Reuse the just-completed registered commit gate only when its executable and
  test input hashes still match the frozen source; otherwise rerun that gate.
  Always run the focused qualification and candidate replay checks. Do not run
  an unregistered raw full pytest suite.
- After every offline gate passes, permit at most one real CommunicationMod
  invocation for r8. Preserve and independently verify either a complete
  qualification terminal or the exact partial/failure boundary, then restore
  configuration and prove protected-state equality and zero target processes.
- A verified complete terminal produces only a handoff for a separate study
  `start` review. Any other result retires r8 permanently and stops; this
  change cannot prepare r9.

Success is one immutable, independently replayable r8 disposition with exact
restoration: either `qualified_for_start_review` or a precise fail-closed
retirement. It is not a favorable gameplay result, trajectory collection, OPE
output, permission to train, or policy promotion.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pre-request-qualification-observability`: authorize one previously absent
  r8 preparation and at-most-once no-action qualification after the reviewed
  source-byte fix, with immutable replay and restoration evidence.
- `noncombat-outcome-evidence-expansion`: define the r8 handoff as a necessary
  but non-authorizing input to the existing separately reviewed study `start`
  gate.

## Impact

- Planning and evidence surfaces: one r8 candidate, request/review package,
  guarded external root, go/no-go record, verifier output, attestation, and
  deterministic closeout. Historical roots and bytes remain unchanged.
- Runtime surfaces are inputs only:
  `scripts/run_noncombat_outcome_evidence_expansion.py`, the trusted launcher,
  `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py`, and the
  existing no-action handshake. No runtime source edit is planned.
- Live boundary: at most one Windows production-Python qualification through
  the real CommunicationMod path after a recorded offline go decision. Before
  publication, rollback is simple candidate abandonment with live state
  unchanged. After publication or invocation, preserve the root, restore the
  exact request-bound configuration, attest inventories and process death,
  and retire the identity on any uncertainty.
- Non-goals: no study `start`, run lock, gameplay action, trajectory, outcome
  inspection, OPE, checkpoint/model mutation, reward or policy change,
  training, promotion, timeout tuning, source repair, r7 retry, or r9
  preparation.
