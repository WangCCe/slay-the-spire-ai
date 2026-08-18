## Context

The training smoke currently creates a seeded random network and compares that same initialization before and after fitting. This proves plumbing but makes candidates from separate runs incomparable. A frozen comparison found r4 and r6 near-tied, so the next experiment needs r4 itself as the training parent and held-out control.

## Goals / Non-Goals

**Goals:**

- Load one explicitly named simulator-only smoke checkpoint before replay insertion.
- Make its online state the trainer online state, target state, immutable control, and optional frozen parent identity.
- Preserve exact file and parameter provenance in both report and successor checkpoint.
- Keep fresh seeded initialization unchanged when no checkpoint is supplied.

**Non-Goals:**

- Load production or RL agent continuation checkpoints.
- Select or tune an anchor-loss weight.
- Claim mechanics equivalence, transfer readiness, or live improvement.
- Start Slay the Spire or CommunicationMod.

## Decisions

1. Add an optional `--initial-checkpoint` to the existing runner instead of a second training program. This keeps transition collection, reward, optimizer, and paired evaluation identical between fresh and warm-start runs.
2. Accept only schema-0 `simulator_training_smoke` checkpoints with `production_compatible=false` and a mapping-valued `online_network_state_dict`. Load through the repository checkpoint reader with CPU mapping and validate the state against the freshly constructed network before any simulator transition is collected.
3. Load the parent state into both online and target networks. The deep-copied loaded state is the held-out control and parameter-delta baseline. Optimizer state and replay are intentionally fresh.
4. Do not enable scalar parent-policy anchor loss in this experiment. Prior live evidence rejected a scalar weight sweep; direct warm-start evaluation answers the current question without another hyperparameter.
5. Record the parent file hash, kind, production flag, and parameter hash. Bind the parent file hash into the successor checkpoint source metadata.

## Risks / Trade-offs

- [A training update may forget early-combat behavior] -> Evaluate battle indices `0,3,6,9` separately and reject live transfer on aggregate or index-specific regressions.
- [A checkpoint may look simulator-only but have incompatible tensors] -> Strict state-dict loading occurs before transition collection.
- [Warm-start randomness may still affect replay sampling and optimizer batches] -> Continue binding behavior and network seeds; run a later independent replication only if the first result is promising.
- [The report schema changes] -> Add fields without changing existing fresh-run behavior, and update the schema version.

