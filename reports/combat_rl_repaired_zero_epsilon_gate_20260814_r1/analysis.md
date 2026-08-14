# Repaired combat RL zero-epsilon gate r1

## Decision

The repaired candidate fails the preregistered promotion gate. Do not continue
training from `rl_combat_model_ep19_steps14035.pth`.

On the same ordered 10-seed pool at `epsilon=0`, the candidate produced 187
total floors versus 233 for the frozen entry baseline. Paired floor results were
1 candidate win, 2 baseline wins, and 7 ties. The candidate also regressed from
4 to 3 Act 2 entries and from 3 to 1 Act 2 boss reaches. Neither arm won a run.

The largest paired regressions were seed #2 (`20` versus `50`) and seed #9
(`16` versus `33`). The only candidate paired win was seed #6 (`22` versus
`21`). Both arms had zero monitored integrity or strict NaN warnings.

## Interpretation

The transition-attribution repair is working operationally, but it does not make
the current learner stable enough for resumed online training. Ten training
games moved the advantage stream by 19.34% and produced worse fixed-policy
outcomes. The next work should target training dynamics rather than collect more
games from this checkpoint.

The highest-priority hypotheses are the fresh replay buffer and freshly copied
target network on resume, combined with preserved Adam moments and immediate
updates. A bounded offline diagnostic should determine whether replay/target
persistence, optimizer reset, a lower update-to-data ratio, or a warm-up period
best constrains early checkpoint drift before another live training batch.
