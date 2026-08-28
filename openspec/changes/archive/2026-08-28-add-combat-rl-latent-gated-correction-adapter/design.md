## Context

The first abstaining residual adapter used continuous state, parent Q values, and the legal mask. Its fixed fit failed because the gate never opened at the registered threshold, and forcing it open caused excessive direct-action drift. A later POC reused the frozen parent's inventory-aware latent representation, pretrained the gate on LightSTS guard-replacement labels, fitted the gate and legal-action head on real development replay, and passed on both an independent replay and a fresh 10-game replay.

The mechanism now needs a reusable implementation boundary before a candidate training runner can be proposed. Production r16 and CommunicationMod must remain untouched during this change.

## Goals / Non-Goals

**Goals:**

- Represent the frozen-parent latent gate and legal-action correction head as a reusable PyTorch module.
- Guarantee exact parent action parity whenever the gate is closed.
- Guarantee that an open gate can select only an action allowed by the supplied mask.
- Provide separate gate and changed-action training losses without allowing parent gradients.
- Provide a versioned development artifact that restores the correction state against an exact parent identity and proves action/telemetry round-trip parity.

**Non-Goals:**

- Do not retrain, tune, or modify production r16.
- Do not create a training cohort, fitted candidate, production checkpoint, or live evaluation.
- Do not route CommunicationMod or `CombatRLAgent` through the adapter.
- Do not claim that replay label agreement implies gameplay improvement.

## Decisions

### Keep latent extraction inside the adapter boundary

The adapter will explicitly use the existing parent card, potion, and relic embeddings plus `hidden_layers` to construct the parent latent representation. It will call the unchanged parent forward path for Q values and verify compatible tensor shapes. This avoids changing the production DQN API or forward semantics.

Alternative considered: add a public latent-returning method to every DQN implementation. That would make extraction cleaner, but it expands the regression surface of the production network for a development-only mechanism.

### Separate gate and correction heads

The gate and action correction will be separate MLPs over the same `parent_latent + parent_q + legal_mask` feature vector. The gate emits one logit. The correction head emits one logit per action and applies the legal mask before `argmax` or cross-entropy.

Alternative considered: one shared head with a joint output. Separate heads preserve the proven POC structure, keep the objectives auditable, and allow a closed gate to discard correction output completely.

### Expose action selection, not synthetic Q values

The adapter will expose components and `select_actions`. It will not pretend correction logits are calibrated Q values. Closed rows select the masked parent `argmax`; open rows select the masked correction `argmax`.

Alternative considered: add correction logits to parent Q values. The failed residual experiment showed that this couples intervention selectivity and Q calibration, obscuring which mechanism failed.

### Freeze and duplicate the parent

The adapter owns a deep copy of the supplied parent, sets it to eval mode, and disables all parent gradients. Training helpers accept only gate/correction optimizer parameters and report parent hashes before and after updates.

### Use a development-only artifact

The artifact stores schema/kind, normalized network metadata, adapter config, exact parent checkpoint and state hashes, gate state, correction state, and caller telemetry. Loading requires the caller to supply the exact parent and expected checkpoint identity. Unknown keys, incompatible shapes, non-finite tensors, or parent mismatch fail closed.

The artifact is explicitly `production_compatible=false`; no generic production checkpoint loader may treat it as an RL v2 training or promoted checkpoint.

## Risks / Trade-offs

- [Risk] The adapter depends on the current DQN embedding and hidden-layer attributes. -> Validate supported parent structure and fail with a clear incompatibility error; do not mutate the parent network API in this change.
- [Risk] Correction logits can be useful for action ranking but are not Q values. -> Expose action selection explicitly and prohibit Q-value packaging claims.
- [Risk] A serialized correction could be paired with the wrong r16 bytes. -> Bind both parent checkpoint SHA-256 and deterministic parent state-dict SHA-256 and require both during load.
- [Risk] A gate threshold at an extreme could silently disable or over-activate correction. -> Validate `0 < threshold < 1` and include gate telemetry in action-selection parity tests.
- [Risk] Development replay agreement may not transfer to live outcomes. -> Keep the artifact non-production and require a later candidate-training and live-evaluation change.

## Migration Plan

1. Add the adapter and artifact helpers behind a new module with no imports from the production agent path.
2. Add regression tests using synthetic RL v2 parents and replay-shaped tensors.
3. Verify focused RL tests and the repository commit gate at the capability boundary.
4. Roll back by deleting or not importing the new module; production r16, agent routing, and CommunicationMod configuration remain unchanged.

## Open Questions

- The later candidate-training change must decide whether to store optimizer state and how to bind the LightSTS/source replay recipe; this mechanism artifact intentionally does neither.
- The later agent-integration change must decide how adapter action telemetry is recorded in live decision traces.
