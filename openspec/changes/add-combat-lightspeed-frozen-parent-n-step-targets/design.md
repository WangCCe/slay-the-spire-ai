## Context

The LightSTS combat runner currently supports ordinary one-step TD targets and
complete-trajectory discounted returns. The former supplies weak temporal credit
assignment, while the latter removes bootstrapping but produced a worse matched
held-out result than the one-step control. The runner already holds complete
trajectories and an exact simulator-only parent network in memory, so a bounded
n-step target can test the middle ground without adding a replay checkpoint
format or touching production gameplay.

The experiment remains CPU-only and simulator-only. Its reports and checkpoints
must bind the initialized parent parameters because those parameters determine
every bootstrap value.

## Goals / Non-Goals

**Goals:**

- Add an opt-in frozen-parent n-step target with an explicit positive horizon.
- Compute targets only from complete, contiguous trajectories.
- Bind horizon, discount, parent parameter identity, bootstrap counts, and
  transformed transition identity in reports and candidate metadata.
- Compare one-step, 3-step, and 5-step candidates on shared fresh training and
  held-out LightSTS profiles.
- Preserve byte-for-byte target preparation behavior for existing modes.

**Non-Goals:**

- Saving or loading a new replay-checkpoint format.
- Changing native rewards, behavior-policy sampling, or network architecture.
- Loading or modifying a production checkpoint.
- Starting Slay the Spire or CommunicationMod.
- Granting transfer, qualification, promotion, or live policy authority.

## Decisions

### Materialize n-step targets before replay insertion

For source transition `t`, the runner will sum at most `n` discounted rewards.
If the trajectory does not terminate within that window, it will add
`gamma^n * max_a Q_parent(s[t+n], a)` using the legal-action mask stored on the
window's final transition. The resulting scalar is stored as the replay reward
and the transformed row is marked terminal, preventing the existing trainer
from adding a second bootstrap term.

This keeps optimizer behavior and replay-buffer contracts unchanged. Extending
the trainer with a second target path was rejected because it would duplicate
batching and masking logic and increase the production-facing surface.

### Bootstrap only from an immutable initialized parent

The bootstrap network is the exact target network produced by successful
simulator-parent initialization, before any replay optimization. Bootstrap
values are computed in evaluation mode under `torch.no_grad()` and are detached
before training starts. The report binds the network parameter SHA-256.

Bootstrapping from the mutable online candidate was rejected because target
values would then depend on optimizer order and would no longer be a frozen-parent
experiment.

### Require complete contiguous trajectories

The n-step mode uses the same `(seed, battle_index, decision_index)` continuity
checks as discounted full returns and requires the complete-trajectory corpus
option. Although n-step targets can be computed for some incomplete prefixes,
accepting them would make tail handling depend on collection bounds rather than
combat outcomes.

### Keep the mode explicitly opt-in

One-step TD remains the default. The new mode has a positive integer horizon,
and existing full-episode-return behavior remains unchanged. Report and
checkpoint schema versions advance so downstream consumers cannot silently
misread the new provenance fields.

### Use a three-arm matched simulator experiment

The first bounded experiment will train one-step, 3-step, and 5-step arms from
the same simulator-only parent, source profiles, optimizer settings, and held-out
profiles. Training and evaluation seeds will be fresh relative to prior runs.
The experiment may identify a candidate for later work, but cannot authorize a
live gate by itself.

## Risks / Trade-offs

- [Frozen parent values may be poorly calibrated] -> Compare both bounded
  horizons with the one-step arm and report per-battle-index paired outcomes.
- [Large target magnitudes may destabilize fitting] -> Preserve the registered
  discount, report target summaries, and reject non-finite bootstrap or target
  values before optimizer work.
- [Target preparation can misalign trajectories and bootstrap rows] -> Require
  contiguous decision indices and cover terminal, short-tail, and exact-horizon
  cases with deterministic unit tests.
- [Native simulator results may not transfer to the game] -> Keep all authority
  flags false and require a separate decision before any real-game validation.

## Migration Plan

1. Add the opt-in mode and deterministic regression coverage.
2. Run focused tests and the relevant repository test gate.
3. Run the registered three-arm matched LightSTS experiment and publish its
   report without changing production configuration.
4. Roll back by removing the opt-in mode and its new report fields; existing
   one-step and discounted-episode-return invocations remain valid.

## Open Questions

None. Horizon selection for any later experiment will be based on the first
matched 3-step and 5-step result rather than tuned on its held-out cohort.
