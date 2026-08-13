## Context

The card-only native-baseline pilot and its bounded continuation changed the
policy parameters without changing any greedy action on the fixed probe set or
improving the development floor. Replay analysis also showed that replacing the
current hash-ridge baseline with a lower-error progress baseline reduced common
bias but made fold gradient directions less stable. A trajectory-level return
therefore does not currently provide sufficiently local, stable card-action
credit for another policy update.

The native non-combat environment is cloneable and already exposes validated
transitions, legal candidates, a native SimpleAgent step, and the formal reward
contract. The POC can use those surfaces without changing production policy or
loading a training checkpoint.

## Goals / Non-Goals

**Goals:**

- Measure terminal-return differences between every legal action at the same
  card-reward source state under a common native continuation policy.
- Prove that evaluating a branch does not mutate the source environment and
  that a fixed branch is exactly reproducible.
- Decide whether action-level counterfactual returns provide enough nonzero,
  uniquely ranked signal to justify a later training-integration proposal.
- Keep the empirical operation bounded to consumed development seeds and a
  fixed branch budget.

**Non-Goals:**

- Fit or update any policy, value function, baseline, or reward model.
- Compare policy quality, run OPE, qualify a checkpoint, or access fresh or
  protected cohorts.
- Change live gameplay behavior, CommunicationMod configuration, production
  checkpoints, or the formal reward contract.
- Tune thresholds, continuation policy, seeds, or branch limits after seeing
  the result.

## Decisions

### Clone once per legal action from an immutable source

The evaluator will canonicalize a card-reward source state, clone it separately
for every legal candidate, apply exactly that candidate, and verify that the
canonical source is unchanged after all branches. This makes action return the
only intentional difference at the branch root. Advancing one shared
environment between alternatives was rejected because it would confound action
choice with simulator state and RNG progression.

### Use native SimpleAgent for every downstream decision

After the forced card action, each branch will use `step_native_baseline()` to
terminal and validate every transition against the formal reward contract. A
learned continuation was rejected because it would require model loading and
would make the credit result dependent on the candidate policy being studied.

### Record source-level viability, not a policy metric

For each complete source state, the report will record action returns, return
spread, whether the best action is unique, and compact hashes of the source and
action sequence. The POC passes only when at least eight source states complete
and at least four have both nonzero spread and a unique best action. These are
signal-availability gates, not evidence that any policy is better.

### Use fixed consumed development support

The run is fixed to seeds `1000..1007`, at most the first two card-reward states
per seed, and at most 64 total action branches. The runner will fail closed on
unsupported simulator behavior or incomplete transitions. It will not replace a
seed, censor a state, or enlarge the branch budget after execution.

### Replay one branch exactly

The first eligible branch will be evaluated a second time from the same source
clone. Initial transition, terminal summary, accumulated reward, and native
action sequence must match exactly. Statistical tolerance was rejected because
the intended native simulator contract is deterministic for an identical clone.

## Risks / Trade-offs

- [Native continuation can be long] -> Enforce the 64-branch ceiling and a
  runner timeout while publishing partial counts only as a failed POC.
- [Common cloned RNG can understate future stochastic variability] -> Treat the
  result only as a local credit-signal viability test; any later training design
  must evaluate robustness across source seeds.
- [SimpleAgent continuation can rank actions differently from a learned policy]
  -> State that the POC measures credit under the fixed native continuation and
  does not claim universal action values.
- [Few seeds may not expose enough card states] -> Use a preregistered minimum
  complete-state gate and stop on failure instead of opportunistically adding
  samples.
- [Large state or action traces can bloat the report] -> Store canonical hashes
  and compact action metadata rather than complete simulator snapshots.
