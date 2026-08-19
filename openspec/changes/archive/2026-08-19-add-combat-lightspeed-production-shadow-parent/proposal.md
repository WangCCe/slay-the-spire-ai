## Why

The current LightSTS training line starts from a simulator-only checkpoint even though the production combat r16 checkpoint has now been shown to use the same RL v2 parameter structure. A fail-closed, hash-bound shadow export is needed so simulator training can start from the actual production policy without mutating it or granting a simulator artifact production authority.

## What Changes

- Add a source-only converter that validates an exact production RL v2 weights checkpoint and exports an explicitly simulator-only shadow checkpoint.
- Prove parameter identity and deterministic masked-Q/action equivalence between the production source and the reloaded shadow on fixed probes.
- Publish an atomic report and manifest binding the source file hash, parameter hash, converter source hash, item vocabulary, and generated shadow artifact.
- Reject incompatible metadata, unexpected checkpoint kinds, hash mismatches, non-tensor state, and failed equivalence checks before publication.
- Keep the source checkpoint immutable, allow only the existing LightSTS simulator-parent loader, and keep the shadow ineligible for CommunicationMod or production RLAgent loading and production promotion.

Success is an exact, independently reloadable simulator shadow whose parameter hash, masked Q-values, and selected actions match the registered production r16 source. Non-goals are gameplay execution, online training, model promotion, source checkpoint mutation, and compatibility conversion across network schemas. The rollback boundary is deletion of the newly generated shadow/report directory; the production checkpoint and live configuration remain unchanged.

## Capabilities

### New Capabilities

- `combat-lightspeed-production-shadow-parent`: Validate a bound production RL v2 checkpoint and export a provenance-complete, simulator-only LightSTS parent with deterministic equivalence evidence.

### Modified Capabilities

None.

## Impact

- Adds one analysis CLI and focused tests.
- Reuses the current RL v2 trainer, item mapper, checkpoint I/O, and LightSTS provenance helpers.
- Produces a new tracked report directory for the exact production r16 shadow.
- Does not change gameplay policy selection, CommunicationMod configuration, production checkpoint loading, or existing simulator training defaults.
