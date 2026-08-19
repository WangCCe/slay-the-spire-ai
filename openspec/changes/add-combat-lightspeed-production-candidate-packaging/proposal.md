## Why

The frozen guarded-control LightSTS checkpoint reproduced a positive reward and HP delta against the production-r16 shadow on 1,683 fresh terminal pairs, but it remains deliberately incompatible with the production RL v2 loader. A deterministic, fail-closed packaging boundary is needed before the exact confirmed weights can be considered for any separately registered live evaluation.

## What Changes

- Add a hash-bound converter that accepts one production-incompatible 328-dimensional LightSTS checkpoint plus the current production-r16 checkpoint and item vocabulary.
- Validate checkpoint classifications, RL v2 metadata, tensor keys, shapes, dtypes, finiteness, dimensions, and caller-supplied hashes before publication.
- Publish an isolated schema-v2 `weights` checkpoint whose online parameters exactly equal the simulator candidate and whose metadata exactly matches the validated production contract.
- Reload the staged checkpoint through the production model path and prove parameter-hash, finite-Q, Q-value, and greedy-action equivalence against the source simulator candidate before atomic publication.
- Publish a manifest and report binding every input, output, provenance field, and authority boundary.
- Keep production r16, CommunicationMod configuration, game processes, and checkpoint discovery paths unchanged.

Success means the packaged checkpoint round-trips with an identical canonical parameter SHA-256, zero action mismatches, zero Q delta on bound probes, and no mutation of any input. Failure leaves no published output. Packaging alone grants no gameplay, qualification, promotion, or production replacement authority.

## Capabilities

### New Capabilities

- `combat-lightspeed-production-candidate-packaging`: Deterministic, hash-closed conversion of an eligible simulator-only RL v2 combat candidate into an isolated production-loadable weights checkpoint with exact equivalence evidence.

### Modified Capabilities

None.

## Impact

- Adds one analysis utility and focused tests adjacent to the existing production-shadow converter.
- Reads the bound simulator checkpoint, production parent checkpoint, and `items.json`; writes only to a new explicit report directory.
- Does not alter training code, reward definitions, LightSTS, the active r16 checkpoint, CommunicationMod configuration, or gameplay behavior.
- Rollback is deletion of the new isolated output directory before any separately registered consumer uses it; existing production state remains byte-unchanged.
