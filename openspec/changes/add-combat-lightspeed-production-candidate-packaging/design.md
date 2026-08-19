## Context

Production r16 is a schema-v2 RL `weights` checkpoint with 328 continuous inputs, 133 actions, and validated item-vocabulary metadata. The confirmed guarded-control artifact contains the same 15 finite tensors and 566,355 parameters, but is intentionally marked `simulator_training_smoke` and `production_compatible=false`. The existing production-shadow converter only reduces authority in the opposite direction.

The packaging boundary must preserve the candidate parameters exactly while preventing a simulator artifact from becoming loadable merely by changing a flag. It must validate both the current production contract and the simulator provenance, publish outside production discovery, and grant no gameplay authority.

## Goals / Non-Goals

**Goals:**

- Convert one explicitly hash-bound, production-incompatible LightSTS candidate into one isolated production RL v2 `weights` checkpoint.
- Reuse the validated production parent's metadata instead of trusting simulator metadata.
- Prove exact tensor, parameter-hash, Q-value, and greedy-action equivalence after production-format reload.
- Publish immutable provenance, report, summary, and manifest artifacts atomically.
- Fail before publication on any classification, hash, metadata, structure, finiteness, or equivalence mismatch.

**Non-Goals:**

- Training, interpolation, candidate selection, reward changes, or simulator evaluation.
- Updating CommunicationMod, checkpoint discovery paths, or the active production checkpoint.
- Authorizing gameplay, qualification, promotion, or simulator-to-game policy quality.
- Supporting encounter-expanded candidates or architecture migration.

## Decisions

1. Add a dedicated `combat_lightspeed_production_candidate.py` utility adjacent to the production-shadow converter. Keeping the reverse authority transition explicit is safer than adding a mode flag to the shadow converter.
2. Require three independently hash-bound inputs: the simulator candidate, the production parent, and `items.json`. The parent is validated with the existing schema-v2 production loader; the candidate receives an equally strict simulator-only loader.
3. Require exact state-dict keys, shapes, dtypes, finite tensors, 328-dimensional architecture, and current RL v2 vocabulary dimensions. Encounter-expanded or production-marked simulator inputs fail closed.
4. Build the production payload from cloned candidate CPU tensors plus the validated parent's RL v2 metadata. Provenance binds input hashes, candidate parameter hash, parent parameter hash, item hash, source commit, converter hash, and the confirmation report hash.
5. Stage the complete output directory, reload the checkpoint through the production checkpoint validator, and compare it to the simulator source. Publication requires matching canonical parameter hashes, zero valid-action Q delta, and zero greedy-action mismatches on deterministic probes.
6. Keep the packaged file outside all production checkpoint discovery directories and mark report authority as packaging-only. A later registration must explicitly consume its hash before any live evaluation.

## Risks / Trade-offs

- [A structurally compatible but semantically stale vocabulary could be packaged] -> Bind the current items file and require the production parent's exact metadata dimensions; record that the simulator source cannot prove its historical item bytes.
- [Packaging can be mistaken for promotion] -> Use a separate output directory, preserve production r16 unchanged, and encode all gameplay and promotion authority as false in the report.
- [Torch serialization bytes are not deterministic across implementations] -> Bind output bytes after publication, but use canonical parameter SHA-256 and reload equivalence as the semantic identity.
- [A later production architecture change could silently align inputs] -> Require exact schema, metadata, keys, shapes, dtypes, and strict network loading on every invocation.

## Migration Plan

1. Implement and test the fail-closed converter without consuming the confirmed candidate.
2. Register the exact candidate, parent, items, converter, output path, and probe contract.
3. Execute packaging once into a new isolated report directory.
4. Review the immutable report before separately deciding whether to register a small matched live gate.

Rollback before any consumer is deletion of only the new isolated output directory. No production file or configuration is changed, so production r16 remains active throughout.

## Open Questions

None. Live evaluation size and promotion criteria remain intentionally outside this change.
