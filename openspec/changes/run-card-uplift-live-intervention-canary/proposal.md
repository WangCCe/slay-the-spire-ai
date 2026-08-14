## Why

The large-corpus card-uplift residual passed an independent counterfactual
audit, a 64-pair fresh simulator evaluation, and a five-game live shadow with
34 disagreements, zero runtime errors, and acceptable latency. The next useful
question is whether those already-trained decisions can safely execute in the
real game; more source-only training does not answer it.

## What Changes

- Add an explicit, source-bound live intervention mode for the frozen card
  uplift model while leaving default gameplay unchanged.
- Substitute only eligible three-card reward decisions; retain Current for all
  other decisions and for every projection, scoring, or action-mapping error.
- Run at most three fresh Ironclad games with no training or exploration and
  publish every attempted substitution, latency, error, run outcome, and model
  binding.
- Disable intervention for the remainder of the canary after the first runtime
  error and automatically stop selecting candidate actions after game three.
- Require at least eight successful substitutions, zero invalid actions, zero
  runtime errors, and latency at most 200 ms for operational success. Record
  floors and victories without making a causal or policy-quality claim.
- Roll back by removing the opt-in canary configuration; no production
  checkpoint or default policy is modified.

## Capabilities

### New Capabilities

- `noncombat-card-uplift-live-intervention-canary`: Opt-in bounded live card
  intervention, per-decision fallback, evidence publication, and rollback.

### Modified Capabilities

None.

## Impact

This touches the existing card-uplift live runtime, `main.py`, the bounded batch
launcher, focused tests, and canary reports. It uses Windows production Python
and CommunicationMod only for the final three-game run. Combat, route, shop,
event, production checkpoints, formal RL training, and default gameplay remain
unchanged.
