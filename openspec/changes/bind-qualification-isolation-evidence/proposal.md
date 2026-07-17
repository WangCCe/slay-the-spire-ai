## Why

Independent review of the prepared r4 qualification found that the prepared
request, terminal result contract, and standalone verifier can pass without
machine-replaying the required CommunicationMod restoration, run/checkpoint/
global-log isolation, or child-process cleanup. This gap must be closed before
any live qualification identity is consumed.

## What Changes

- Bind one compact canonical pre-qualification isolation baseline directly in
  the reviewed request. The baseline covers raw CommunicationMod bytes, the AI
  marker, run-record inventory, the registration-selected checkpoint inventory,
  global AI logs, and the absence of a pre-existing qualification child.
- Recollect the same resources after the no-action child exits, require exact
  equality before publishing a passing terminal result, and bind the post-state
  plus child-liveness observation in that result.
- Make the standalone verifier independently recollect and compare the current
  restored state with the request baseline and terminal observations before it
  can publish a verified attestation.
- Add red-first producer, lifecycle, and verifier regressions for every omitted,
  malformed, drifted, or still-live isolation component.
- **BREAKING**: advance the qualification request/result schemas and exact
  fixtures; old terminal evidence remains historical but cannot qualify a new
  launch under the strengthened contract.
- Keep r4 unlaunched and unconsumed. Regenerate registration/source/request
  bindings and obtain a fresh reviewed launch amendment after this repair; do
  not create a run lock, collect games, train, tune, or change gameplay policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-outcome-evidence-expansion`: replace external-only broad-isolation
  claims with a request-bound baseline, terminal equality proof, and independent
  verifier replay required before launch qualification can pass.

## Impact

- Affected code: `scripts/run_noncombat_outcome_evidence_expansion.py`,
  `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py`, their
  focused tests, exact registration fixtures, and the pending r4 planning
  artifacts.
- Live evidence: the current r4 root contains only its static config and has no
  active request, handshake, terminal, game, or study artifact; it remains
  outside the rollback boundary while this offline repair is developed.
- Success metric: a passing independent audit proves exact baseline equality for
  every bound resource and proves the recorded child PID is no longer alive;
  any mismatch fails closed with uniformly false study/training/policy
  authority.
- Rollback boundary: no live process or registered study state may start during
  this change. If implementation or exact registration bytes change, preserve
  the old candidate as historical and create a newly reviewed candidate rather
  than weakening or bypassing the isolation checks.
