## Context

The archived combat LightSTS bridge POC produced exact RL v2 shapes and deterministic supported successors across 32 fixed seeds. It did not generate replay or invoke `DQNTrainerV2`. The next useful question is whether native transitions can drive the existing optimizer and produce a technically valid disposable candidate without touching production r16 or the game.

## Goals / Non-Goals

**Goals:**

- Generate bounded simulator-only RL v2 transitions from fixed first-combat seeds.
- Exercise the existing replay buffer and `DQNTrainerV2` on CPU from a deterministic fresh initialization.
- Compare the same initialized policy before and after fitting on disjoint fixed simulator seeds.
- Publish transition, reward, loss, parameter-delta, unsupported-boundary, and paired evaluation metrics with source hashes.

**Non-Goals:**

- Load, modify, or imitate r16 or any other production checkpoint.
- Claim that LightSTS rewards, mechanics, or policy rankings transfer to the game.
- Start Slay the Spire or CommunicationMod, collect live evidence, qualify, or promote a candidate.
- Tune architecture, reward weights, seeds, or hyperparameters after observing this smoke.

## Decisions

1. **Use fixed disjoint source-only cohorts.** The default smoke uses `0..255` for transition generation and `10000..10063` for held-out evaluation, with bounded decisions and actions per turn. Disjoint cohorts make the before/after comparison informative without consuming live seeds. Ad hoc continuation seeds were rejected because they would weaken reproducibility.

2. **Use a seeded network-independent behavior policy.** A deterministic PRNG chooses among legal non-End-Turn actions, with a per-turn cap that forces End Turn. This gives more action variety than the calibration policy while keeping the transition corpus identical regardless of optimizer behavior. Online epsilon-greedy collection was rejected because pre/post policy changes would confound the smoke.

3. **Use an explicit native reward subset.** Rewards include production-compatible coefficients for monster damage, kills, all-lethal, player HP loss ratio, and turn end, computed only from before/after native snapshots. Unknown production-only reward channels are omitted and reported. Constructing permissive CommunicationMod `Game` objects was rejected because it would hide missing semantics.

4. **Train a fresh disposable RL v2 network on CPU.** Seed Python, NumPy, and Torch; create `DQNTrainerV2` without parent anchors or production weights; insert accepted transitions and call its normal train step. Preserve the initial state dict in memory for the held-out control. Reusing r16 was rejected because simulator reward mismatch could contaminate a production lineage.

5. **Treat unsupported successors as excluded, not terminal.** If an action reaches `CARD_SELECT` or another unsupported boundary, do not fabricate a next observation and do not store that pending transition. Record the reason and end that simulator episode. Treating unsupported as terminal was rejected because it would inject false reward targets.

6. **Make the verdict technical, not promotional.** Ready requires accepted replay transitions, finite optimizer losses, non-zero parameter change, and complete paired held-out evaluation. Uplift is reported but not required. The output checkpoint is marked simulator-only and cannot satisfy production checkpoint metadata or promotion gates.

## Risks / Trade-offs

- **The fixed behavior policy may be weak.** -> This is a pipeline smoke, so publish its action distribution and do not infer policy quality from the corpus.
- **The reward subset may rank actions differently from live reward.** -> Bind the reward definition in source and require real-game divergence work before transfer claims.
- **First combats provide narrow deck and encounter coverage.** -> Report card, action, encounter, and unsupported coverage; expand only in a later registered experiment.
- **A fresh network may not improve in one smoke.** -> Require optimizer and evaluation completion, not uplift; use the result to size a larger simulator experiment.
- **CPU training can still be slow.** -> Bound seeds, decisions, replay size, and train calls; do not run the repository-wide pytest suite for this isolated runner.

## Migration Plan

There is no production migration. The runner is opt-in, writes only to a new report directory, and never changes CommunicationMod configuration or production checkpoints. Rollback removes the runner, tests, and simulator-only artifacts.

## Open Questions

- Whether the first smoke produces enough held-out signal to justify a larger simulator experiment rather than broader state-import work.
- Which live divergence metrics should eventually gate simulator-trained candidate transfer to real-game qualification.
