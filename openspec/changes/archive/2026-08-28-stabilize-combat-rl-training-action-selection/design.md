## Context

`DQNTrainerV2.select_action()` calls the online network while the trainer owns it in its default train mode. The dueling network inherits a hidden Dropout layer, so zero-epsilon replay collection samples a stochastic policy even though the same checkpoint runs deterministically under production `--eval`. Fresh provenance evidence found 44 eval-parent disagreements among 239 direct unmodified actions.

The collection still needs `--train` so transitions and checkpoints are persisted. The fix therefore must separate behavior inference mode from the mode used by optimizer updates without changing the CLI or replay schema.

## Goals / Non-Goals

**Goals:**

- Use inference semantics for every greedy online-network behavior action selected by the trainer.
- Restore the network's exact prior training flag after selection, including exceptional exits.
- Preserve epsilon exploration and the current optimizer-update mode.
- Demonstrate deployment parity on a bounded fresh zero-update r16 replay.

**Non-Goals:**

- Removing Dropout from training updates or changing network architecture.
- Changing epsilon schedules, guards, rewards, action masks, or replay provenance.
- Training, qualifying, promoting, or replacing a candidate in this change.

## Decisions

### Switch mode only around the greedy forward pass

`select_action()` will capture `online_network.training`, call `eval()`, execute the masked greedy forward pass under `torch.no_grad()`, and restore the captured flag in `finally` through `train(previous_mode)`.

This is narrower than keeping the online network permanently in eval mode, which would also disable Dropout during optimizer updates. It also avoids cloning a second behavior network that could drift from the online weights.

### Leave epsilon exploration untouched

The random-action branch returns before the network mode boundary. It does not execute a forward pass today, so changing module mode there would add no parity benefit and would broaden the behavioral surface.

### Require fresh deployment-parity evidence before training

The previous cohort remains immutable provenance evidence but is not training input. A new registered zero-update cohort will require all direct unmarked actions to equal frozen r16 eval-mode greedy actions while preserving legal nonzero overrides and zero weight updates.

## Risks / Trade-offs

- [Online training trajectories change because Dropout no longer perturbs behavior selection] -> This is the intended deployment-parity correction; epsilon remains the explicit exploration mechanism and fresh replay evidence measures the result.
- [An exception could leave the network in eval mode] -> Restore the captured mode in `finally` and cover the path with a failing forward-pass regression.
- [Optimizer updates could accidentally run in eval mode] -> Test that a trainer starting in train mode is restored before the next update path and keep update code unchanged.
- [A deterministic direct-action check could still fail due to another source of randomness] -> Stop before training and investigate the fresh trace rather than relabeling the mismatch.

## Migration Plan

1. Add RED regressions for deterministic greedy selection and mode restoration.
2. Implement the temporary inference-mode boundary in `select_action()`.
3. Run focused trainer tests and the qualified commit gate, then commit before gameplay.
4. Register and collect one fresh zero-update r16 cohort on unused seeds.
5. Proceed to a separate provenance-aware training change only after 100% direct-action parity.

Rollback is a single-method revert. Checkpoint, replay, and CommunicationMod formats do not change.

## Open Questions

None.
