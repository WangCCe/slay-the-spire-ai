## Context

Production combat r16 is stored as a `checkpoint_kind=weights` RL v2 checkpoint, while the LightSTS trainer intentionally accepts only `checkpoint_kind=simulator_training_smoke` parents with `production_compatible=false`. A read-only audit established that r16 and the current LightSTS network have identical state-dict keys, shapes, dtypes, and 566,355 parameters. The remaining gap is an explicit, reproducible authority boundary between the production artifact and a simulator-only copy.

## Goals / Non-Goals

**Goals:**

- Fail closed unless the input is the exact registered production weights file and matches the current RL v2 architecture and item vocabulary.
- Export a shadow with byte-for-byte tensor values but simulator-only checkpoint semantics.
- Prove the exported checkpoint can be reloaded strictly and produces identical masked Q-values and actions on deterministic probes.
- Bind every published artifact to source, vocabulary, converter, and parameter hashes.

**Non-Goals:**

- Modify, rename, or reclassify the production checkpoint.
- Make the shadow loadable by CommunicationMod or eligible for direct promotion.
- Migrate parameters between different schemas or vocabularies.
- Run gameplay, training, evaluation, OPE, or model selection inside the converter.

## Decisions

1. **Use a standalone source-only CLI.** The converter will reuse public checkpoint, mapper, trainer, and hashing helpers but remain separate from the training runner. This keeps conversion authority and training authority independently auditable. Embedding conversion in the training runner was rejected because it would blur fail-closed parent validation.
2. **Require an expected source SHA-256.** Paths alone are mutable. The CLI will resolve the source, items file, and output paths, then verify the exact production file hash before loading tensors.
3. **Validate the production contract before copying.** The root must be a mapping with `checkpoint_kind=weights`, schema version 2, `network_type=dueling`, and metadata matching the current action/state slots and the mapper-derived vocab sizes. The state dict must be nonempty and tensor-only and must load strictly into a fresh current trainer.
4. **Copy tensors into an authority-reduced envelope.** The shadow will contain `checkpoint_kind=simulator_training_smoke`, `production_compatible=false`, `source_type=production_rl_v2_shadow`, and copied CPU tensors under `online_network_state_dict`. Provenance will preserve source hashes and metadata, allow the existing LightSTS simulator-parent loader, and remain structurally invalid for the production RLAgent metadata loader.
5. **Use deterministic functional equivalence probes.** Fixed continuous/id inputs and masks will be run through independent source-loaded and shadow-reloaded trainers in evaluation mode. Publication requires matching parameter hashes, no action mismatch, and a bounded maximum valid-action Q delta.
6. **Publish last.** The CLI will build the checkpoint and reports in a staging directory, reload and verify them there, write a manifest with artifact hashes, then atomically rename the staging directory to the final absent output path.

## Risks / Trade-offs

- [A future RL v2 metadata change makes a valid checkpoint fail validation] -> Keep validation explicit and versioned; add support through a new reviewed change rather than permissive inference.
- [The items file changes while dimensions remain equal] -> Bind and report the exact items SHA-256 and mapper vocabulary sizes.
- [A copied checkpoint is mistaken for production-ready] -> Set both simulator-only kind and `production_compatible=false`, explicitly allow only simulator-parent loading, prove the production RLAgent rejects the envelope, and do not expose a production packaging path.
- [Fixed probes miss a subtle serialization issue] -> Also require strict state-dict loading, exact keys/shapes/dtypes, and an unchanged canonical parameter hash.
- [The production checkpoint records vocabulary sizes but not its historical `items.json` hash] -> Bind the current file hash, require exact dimension agreement, and report that historical ID-order identity remains an explicit assumption rather than proven provenance.
- [Partial output is mistaken for a completed conversion] -> Publish only by an atomic directory rename after all checks and manifest writes succeed.

## Migration Plan

1. Add focused converter tests and implementation.
2. Convert the exact hash-bound production r16 checkpoint into a new report directory.
3. Verify and commit the shadow artifact and report without changing live configuration.
4. Register a separate one-step LightSTS experiment that consumes the shadow through the existing simulator-only parent contract.

Rollback removes only the new converter, tests, OpenSpec change, and generated shadow report. No production artifact or configuration requires restoration.

## Open Questions

None. A production packaging or live promotion path, if justified by later evidence, requires a separate decision and artifact.
