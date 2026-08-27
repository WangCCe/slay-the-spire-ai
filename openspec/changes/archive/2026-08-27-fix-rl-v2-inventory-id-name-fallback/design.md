## Context

The exported `items.json` used by RL v2 contains canonical display names for potions and relics, while CommunicationMod objects often expose internal IDs such as `FairyPotion`, `Self Forming Clay`, or `MawBank`. `StateEncoderV2` currently asks `IdMapper` to resolve only the first identity returned by `potion_id()` or `relic_id()`, so an occupied object becomes categorical zero whenever that internal ID is not a display-name vocabulary key. The LightSTS bridge already avoids this failure by trying both simulator ID and name.

The r14 and r15 runtime evidence can be joined one-to-one to their replay transitions after filtering the five in-combat action types. Across all 7,685 joined transitions, every observed occupied potion or relic whose internal ID was unknown had a display name that resolved to an existing numeric ID.

## Goals / Non-Goals

**Goals:**

- Encode real potion and relic objects with an existing stable ID whenever either their preferred identity or display name resolves.
- Preserve exact vocabulary, tensor, and checkpoint dimensions.
- Prove the historical coverage and revise the calibration interpretation with immutable, reproducible evidence.

**Non-Goals:**

- Do not mutate r14/r15 replay snapshots or production checkpoints.
- Do not retrain, promote, or run the game as part of this change.
- Do not infer that all remaining LightSTS/replay mismatch is simulator mechanics divergence.

## Decisions

1. **Fallback belongs at the object-encoding boundary.** `StateEncoderV2` will keep the existing preferred identity lookup and only try `object.name` when that lookup returns zero. This preserves `IdMapper`'s name-keyed vocabulary and avoids introducing unbounded aliases or changing numeric assignment. Making `IdMapper` normalize arbitrary strings was rejected because it would obscure provenance and affect unrelated callers.

2. **Known identity wins.** If the preferred identity already resolves, its current value remains authoritative. Name fallback is used only for unknown preferred identities, and empty `Potion Slot` values remain zero. This makes the behavior backward compatible for already-encoded objects.

3. **Historical correction is additive and read-only.** A focused audit will load immutable trace archives and complete replay snapshots, require an exact chronological `(floor, action-family)` join, and report preferred-ID, fallback, unresolved, and encoded-versus-corrected occupancy counts. It will not overwrite source tensors.

4. **Calibration correction does not erase the initial report.** The addendum will bind the original r2 calibration and explain which inventory signal was source-encoder undercount. Residual simulator/replay differences remain descriptive until separately attributed.

5. **Training follows corrected data readiness.** Existing r16 remains load-compatible, but newly nonzero embeddings may be weakly trained. A separate decision will determine whether to reconstruct corrected replay or collect fresh real replay before any formal training.

## Risks / Trade-offs

- **Previously unseen embedding values can change r16 decisions** -> keep the fix checkpoint-compatible but require a fresh offline/live validation boundary before production promotion.
- **Trace/replay join could drift or silently misalign** -> fail unless source counts, floor sequence, and normalized action-family sequence match exactly.
- **Display names could be missing or ambiguous in future data** -> retain zero for unresolved names and publish unresolved identities; do not invent fuzzy matching.
- **The initial calibration attribution is already committed** -> publish a bound correction addendum rather than rewriting historical evidence.

## Migration Plan

1. Add red regressions for real internal-ID/display-name pairs and empty slots.
2. Add the minimal encoder fallback and run focused tests.
3. Run the historical coverage audit against r14/r15 and publish an addendum.
4. Run one optimized commit gate, then commit and push the coherent change.
5. Keep original checkpoints unchanged; revert the commit if fresh validation shows a regression.

## Open Questions

- Whether the next training corpus should be reconstructed from the exact trace join or collected fresh after the encoder fix remains a downstream evidence decision.
