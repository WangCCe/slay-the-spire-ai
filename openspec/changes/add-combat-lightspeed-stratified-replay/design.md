## Context

LightSTS training collects profiles uniformly by requested battle index, but naturally fewer seeds reach later indices. The replay buffer then samples transitions uniformly without retaining a stratum identity. The latest anchored run had initialized profile counts `256/246/205/154` for indices `0/3/6/9` and still materially regressed index 9.

## Goals / Non-Goals

**Goals:**

- Preserve requested battle index on every collected transition.
- Report source and prepared replay counts per index.
- Offer a deterministic, opt-in way to equalize replay stratum counts without changing trainer or replay-buffer core behavior.

**Non-Goals:**

- Change profile reachability, reward, network architecture, or optimizer budget.
- Drop source transitions or fabricate new state/action values.
- Tune the parent-action weight or combine multiple new variables.
- Enable stratification by default or affect production replay.

## Decisions

1. Add `battle_index` as analysis metadata on the runner-local `ReplayTransition`; insertion into `DQNTrainerV2` remains unchanged.
2. In stratified mode, group all source transitions by configured battle index, retain each source row once, then deterministically repeat shuffled rows in smaller strata until every group equals the largest source group. Missing strata are technical blockers.
3. Interleave prepared groups round-robin by sorted battle index. This prevents insertion order from containing large contiguous duplicated blocks and makes preparation reproducible from an explicit seed.
4. Report source counts, prepared counts, duplicate counts, target count, and seed. Default mode reports identical source/prepared counts and zero duplicates.
5. Keep r4 warm start, parent-action weight `1.0`, optimizer steps `256`, and all other settings unchanged from the preceding experiment while using new train/evaluation seeds.

## Risks / Trade-offs

- [Oversampling can overfit later transitions] -> Keep the optimizer budget fixed and require fresh held-out per-index guardrails.
- [Long combats may already dominate transition counts despite fewer profiles] -> Base balancing on measured transition counts, not profile counts, and publish both.
- [Duplicate order may affect deterministic sampling] -> Bind an explicit preparation seed and round-robin order.
- [A missing reachable stratum could be hidden] -> Fail rather than silently falling back to unstratified replay.

