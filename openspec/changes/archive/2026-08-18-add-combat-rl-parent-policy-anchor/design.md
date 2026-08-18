## Context

RL v2 currently resumes the online, target, optimizer, and replay state from a training checkpoint, then optimizes only Double-DQN TD loss. Two continuations from the promoted parent improved retained-replay TD metrics but regressed fresh matched live outcomes. The implementation must preserve CommunicationMod compatibility, keep evaluation unchanged, and support both an initial anchor from an existing schema-2 checkpoint and exact anchored checkpoint resume.

## Goals / Non-Goals

**Goals:**
- Preserve the starting parent policy during an explicitly anchored RL v2 continuation.
- Keep the anchor frozen and mask-aware so it never teaches an invalid action.
- Persist enough state for exact anchored resume.
- Leave all existing training and evaluation paths unchanged when the weight is zero.

**Non-Goals:**
- Tune the anchor weight automatically.
- Change TD targets, reward shaping, replay sampling, epsilon, or expert mixing.
- Support RL v1 or use offline metrics as promotion authority.

## Decisions

### Use masked greedy-action distillation

For every sampled replay state, the frozen parent network selects its greedy action under the stored action mask. The trainable online network receives cross-entropy loss against that action, and the trainer minimizes:

`total_loss = td_loss + parent_policy_anchor_weight * anchor_loss`

This directly protects the decision surface implicated by the live regressions. Weight-space L2 was rejected because parameter distance does not map cleanly to masked action preservation, and checkpoint averaging already failed to improve live outcomes.

### Anchor the checkpoint supplied to the continuation

A positive anchor weight requires RL v2 training and an explicit or auto-resolved starting checkpoint. On the first anchored continuation, the trainer freezes a copy of that checkpoint's online network. Evaluation, fresh training without a checkpoint, and RL v1 reject a positive anchor weight.

### Persist the original frozen anchor

Anchored checkpoints include the configured weight and the frozen anchor network state. Resuming with a positive weight restores that state rather than anchoring to the successor's current online network. Existing schema-2 checkpoints have no anchor state and remain valid initial parents.

### Keep the option disabled by default

The CLI and batch wrapper expose `--parent-policy-anchor-weight`. The default is `0.0`; in that state the trainer does not allocate an anchor network or compute anchor loss, and checkpoint loading remains backward compatible.

## Risks / Trade-offs

- [Anchor weight is too high and blocks useful learning] -> Start with one bounded fixed-weight smoke and require both TD improvement and materially higher parent greedy agreement before a fresh live gate.
- [Anchor weight is too low to prevent forgetting] -> Report anchor and TD losses separately and reject the candidate without changing the registered run mid-flight.
- [Masked logits contain negative infinity] -> Derive the parent label from a mask with at least one valid action and test finite total loss and gradients explicitly.
- [Checkpoint size increases] -> Store the frozen anchor only when the feature is enabled; unanchored checkpoints are unchanged.

## Migration Plan

1. Add regression tests for disabled behavior, frozen masked anchor loss, invalid configuration, and checkpoint resume.
2. Implement trainer, agent, CLI, and batch-wrapper plumbing.
3. Run focused tests and the repository test gate.
4. Run one bounded anchored training smoke from the promoted parent without changing production configuration.

Rollback is to omit the option or set it to `0.0`; existing checkpoints and production eval configuration remain valid.

## Open Questions

The initial fixed anchor weight is an experiment parameter, not a new default. Its value will be frozen before the bounded smoke and will not be changed within that run.
