## Why

The CPU action-relative live shadow passed every registered readiness condition
over five real games, including 241 eligible guard replacements, 66 candidate
intervention intents, zero runtime errors, and 7.244ms p95 latency. The artifact
still has no action authority, so a bounded matched live gate is now the
smallest experiment that can determine whether those intervention intents
improve real gameplay rather than only replay or shadow metrics.

## What Changes

- Add an explicit, source-bound, eval-only action-relative candidate mode that
  may replace a completed outer-guard action only after a fixed safety veto.
- Preserve parent, guard, candidate, veto, selected, and final action evidence;
  fail closed to the guard action on any identity, legality, safety, or runtime
  error.
- Add batch-wrapper isolation for the new candidate registration and keep it
  mutually exclusive with every existing combat shadow or candidate runtime.
- Pre-register one ten-seed Ironclad A0 candidate arm and one production-r16
  parent arm in identical seed order, then reconcile runs, traces, logs, and
  exact production-config restoration.
- Qualify only on fixed paired non-regression and technical conditions. A pass
  permits a separate promotion decision; it does not promote automatically.
- Do not train, fit, tune, change the artifact threshold, or retry a completed
  cohort under a different interpretation.

## Capabilities

### New Capabilities

- `combat-rl-action-relative-matched-live-gate`: Source-bound late candidate
  takeover, safety veto, full action provenance, and matched live qualification.

### Modified Capabilities

None.

## Impact

- Runtime: `spirecomm/ai/rl/v2/agent.py`, the action-relative live runtime, and
  the outer `CombatRLAgent` finalization boundary.
- Launch isolation: `scripts/run_training_batch.py` and its environment tests.
- Evidence: a fixed ten-pair live gate using the existing production-r16
  checkpoint and already qualified action-relative artifact.
- Success metric: candidate paired floor wins exceed losses, at least one pair
  differs, total floors and Act 2/Act 2 boss/Act 3/victory counts are non-worse,
  candidate takeover occurs, and every identity, safety, completion, error, and
  restoration check passes.
- Rollback: omit the candidate registration and restore the byte-identical
  CommunicationMod production config; the production checkpoint and artifact
  are never modified.
