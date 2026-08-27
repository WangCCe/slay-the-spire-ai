## Why

An exact chronological join of the r14/r15 real decision traces to all 7,685 replay transitions found that the RL v2 encoder under-recorded occupied inventory: 1,904 potion occurrences and 1,478 relic occurrences had an internal object ID absent from the exported name-keyed vocabulary even though the same object's display name resolved to an existing stable numeric ID. Training or evaluating against those zero-coded states would hide real inventory context and would also make the LightSTS-to-replay distribution comparison misleading.

## What Changes

- Make RL v2 potion and relic encoding try the existing object identity first, then the object's display name when the first lookup is unknown.
- Preserve empty potion slots as zero and preserve every existing vocabulary entry, numeric ID, vocabulary size, tensor shape, and checkpoint structure.
- Add regressions using internal-ID/display-name pairs observed repeatedly in r14/r15 traces.
- Publish a deterministic read-only coverage audit that measures how much of the historical r14/r15 inventory undercount the fallback explains and corrects the interpretation of the initial replay distribution calibration.
- Treat a complete resolution of known occupied aliases with no changes to already-known or empty identities as the success metric.
- Do not overwrite historical checkpoints, start gameplay, train a policy, alter LightSTS mechanics, or claim that the remaining simulator/replay distribution differences are causal.
- Roll back by reverting the encoder fallback commit; original checkpoints and evidence remain immutable.

## Capabilities

### New Capabilities

- `rl-v2-inventory-identity-encoding`: Defines checkpoint-compatible potion and relic identity fallback plus auditable historical coverage.

### Modified Capabilities

- `combat-lightspeed-replay-distribution-calibration`: Requires calibration interpretation to distinguish source encoder undercount from simulator progression differences when exact trace evidence is available.

## Impact

- Production encoding: `spirecomm/ai/rl/v2/state_encoder.py` and focused RL v2 tests.
- Offline evidence: a narrow analysis script and report derived from immutable r14/r15 runtime evidence and replay checkpoints.
- Existing r16 checkpoint dimensions remain compatible, but historical replay tensors are not mutated and remain known to contain zero-coded inventory aliases.
