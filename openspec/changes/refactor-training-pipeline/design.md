## Context
The current training loop is tied to a live Slay the Spire process through Communication Mod. This is reliable for ground-truth gameplay but slow, UI-bound, and prone to degradation during long sessions as logs and run records accumulate. Recent runs indicate the model is collecting many similar failures: early Act 1 elite deaths under aggressive routing.

## Goals
- Make live training safer and easier to resume by running bounded batches with explicit metrics.
- Reduce wasted samples by using curriculum routing before aggressive elite exposure.
- Keep the active game directory small enough to avoid end-of-run lag.
- Create reusable offline training data from `.run` files and logs so model updates are not limited to live UI speed.
- Add checkpoint promotion criteria based on empirical run statistics.

## Non-Goals
- Replace Slay the Spire with a full game simulator.
- Rewrite the RL algorithm from DQN to PPO or another algorithm.
- Change the Communication Mod protocol.
- Remove existing `SimpleAgent`, `OptimizedAgent`, or `combat_rl` behavior.

## Decisions
- Decision: Use a batch orchestrator script instead of embedding all training supervision directly into `main.py`.
  Rationale: `main.py` already handles live protocol timing; orchestration, analysis, restarts, and checkpoint promotion are easier to test and maintain outside the communication loop.

- Decision: Curriculum defaults start with conservative Act 1 elite routing.
  Rationale: Recent data shows aggressive Act 1 elites dominate failures. The model needs longer trajectories before it can learn meaningful post-Act-1 behavior.

- Decision: Offline data generation should use standard-library JSON/CSV artifacts first.
  Rationale: The project prefers minimal dependencies. PyTorch remains optional for model training, while data extraction and analysis should run without it.

- Decision: Checkpoint promotion requires bucketed run metrics, not just training loss.
  Rationale: Loss can improve while policy quality declines. Promotion should consider average floor, elite death rate, boss reach rate, and action failure rate.

## Risks / Trade-offs
- More orchestration scripts can increase operational complexity. Mitigation: keep the first version file-based and command-line driven.
- Conservative routing may under-train elite tactics. Mitigation: add staged risk schedules that reintroduce elites once the model consistently reaches Act 1 bosses.
- Offline artifacts may not contain enough per-decision detail if logs are sparse. Mitigation: define required logging fields and fall back to `.run`-level imitation/evaluation where action traces are unavailable.

## Migration Plan
1. Keep existing `main.py --agent combat_rl --train` usable.
2. Add a wrapper for bounded batches with conservative defaults.
3. Add analysis gates that summarize the batch and decide whether a checkpoint is promotable.
4. Add offline extraction for existing `.run` files and `ai_debug.log`.
5. Gradually add imitation/pretraining support once artifacts are validated.

## Open Questions
- Should the first curriculum threshold be based on average floor, boss reach rate, or both?
- Should process restart automation launch Slay the Spire directly, or only emit a stop/restart recommendation for manual control?
- How much debug logging can be added without slowing Communication Mod gameplay?
