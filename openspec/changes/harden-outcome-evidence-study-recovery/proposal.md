## Why

The registered 2026-07-15 outcome-evidence study exposed two fail-closed lifecycle gaps: the standalone verifier rejects every ledger with a global stop before it can verify a valid blocked closeout, and the runner claims a slot before the real child process proves it can receive CommunicationMod state. The first gap leaves the deterministic blocked closeout independently unverifiable; the second converted a startup communication failure into an invalid terminal slot.

## What Changes

- Add an independent blocked-closeout verifier branch driven by the validated ledger and finalization claim. It will replay the exact blocked closeout, require all authority gates false, and require every normal pool/OPE artifact to be absent.
- Preserve the existing normal all-slot verifier branch and historical registration support; branch selection will not trust a report label or operator argument.
- Add a three-record, child-specific CommunicationMod handshake. The parent must publish an exclusive preclaim-attempt before `Popen`; the real gameplay child must then receive and parse an initial state without callbacks or actions, publish a run-lock-bound ready record, and wait for the parent release.
- Move `slot_started` after verified readiness and an unchanged preclaim AI marker boundary but before release. A timeout, early exit, orphaned attempt, malformed ready record, binding mismatch, or preclaim output mutation will record a global stop while the slot remains unlaunched.
- Make the handshake contract explicit in future registrations and run locks while keeping normal gameplay inert when the study handshake environment is absent.
- Do not create a new registration, launch a replacement collection, run OPE, train, tune, change gameplay policy, or reuse the blocked 2026-07-15 artifact root in this change.

Success requires the frozen 2026-07-15 blocked artifact to pass independent verification, deterministic tamper cases to fail closed, handshake failure to leave the next slot unlaunched with no exploration manifest or trace, handshake success to preserve launch-at-most-once accounting, focused and full Windows pytest to pass, and strict OpenSpec validation to remain green.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-outcome-evidence-expansion`: require independently replayable blocked closeouts and a verified preclaim CommunicationMod handshake for future registered slot launches.

## Impact

- Primary code: `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py`, `scripts/run_noncombat_outcome_evidence_expansion.py`, `analysis_scripts/noncombat_outcome_evidence_expansion.py`, `main.py`, and a small shared handshake module if needed.
- Tests: outcome-evidence verifier, runner, finalizer, registration, and normal-runtime startup regressions.
- Live systems: CommunicationMod stdin/stdout startup for explicitly configured registered studies only. The production Windows Python path and ordinary no-handshake gameplay behavior remain unchanged.
- Compatibility: the verifier must continue to read the existing v1 blocked artifact; only newly created registrations may require the new handshake contract.
- Rollback boundary: remove the explicit study handshake environment and use the ordinary bounded `--eval` CommunicationMod command. No checkpoint, policy artifact, old study artifact, or outcome threshold is modified.
