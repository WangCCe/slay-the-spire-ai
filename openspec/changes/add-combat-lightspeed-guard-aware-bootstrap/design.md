## Context

The LightSTS runner now supports frozen production-r16 guarded replay behavior, raw or proxy-aware parent anchors, one-step TD, complete discounted returns, and frozen-parent bounded n-step returns. Guarded collection changes the action executed in the simulator, but target construction remains bare-policy based: one-step TD selects the next action with the candidate online network's legal `argmax`, and frozen-parent n-step uses the initialized parent's maximum legal next-state Q value. Neither path applies the deployment guard at the bootstrap state.

This distinction affects a large part of the corpus. The fresh optimizer-dose cohort recorded 21,241 guard replacements among 51,560 accepted transitions. Proxy-aware current-row anchor labels were negative, which leaves next-state target policy alignment as a separate unresolved interaction.

## Goals / Non-Goals

**Goals:**

- Add an explicit opt-in frozen-parent deployment-guard bootstrap policy for bounded n-step target transformation.
- Make the target-policy action deterministic and independent of epsilon behavior exploration.
- Validate every nonterminal bootstrap action against its aligned next-state action mask before replay insertion or optimization.
- Bind parent identity, action provenance, replacement counts, and raw-max versus guarded-action Q-gap evidence.
- Preserve the current raw-greedy bootstrap and all one-step behavior by default.

**Non-Goals:**

- Change the production deployment guard or its native-reward selection rule.
- Change `ReplayBufferV2`, production checkpoint schemas, reward weights, optimizer settings, or live agent behavior.
- Fit, evaluate, package, or promote a candidate as part of this change.
- Start Slay the Spire or CommunicationMod.

## Decisions

### Keep target-policy and behavior actions separate

Guarded-parent collection will compute the deterministic frozen-parent raw action and its deployment-guard transformation for every supported state below the action cap before applying the epsilon branch. The resulting target-policy action and whether the target guard replaced raw EndTurn are retained separately from the action actually executed and the existing behavior replacement flag.

This ensures epsilon changes corpus coverage without changing the policy being evaluated by bootstrap targets. Reusing the executed action was rejected because exploration rows would turn the target into behavior-policy SARSA and make the target depend on epsilon.

### Align next-state actions through complete trajectory identity

Each in-memory transition will retain its current target-policy action. For a nonterminal row, the bootstrap action is the target-policy action on the immediately following contiguous row with the same `(seed, battle_index)` identity. Terminal rows have no bootstrap action. Guard-aware mode will require complete contiguous trajectories and fail if a successor row is absent, duplicated, out of range, or illegal under the stored next-action mask.

Computing a second parent decision directly from encoded next-state tensors was rejected because applying the deployment guard also requires the native environment and native reward comparison. The next trajectory row already represents that exact supported state and control context.

### Transform targets before generic replay insertion

The existing frozen-parent n-step transformation will gain a bootstrap policy mode:

- `frozen-parent-raw-greedy-v1` remains the default and gathers the maximum legal parent Q value.
- `frozen-parent-deployment-guard-v1` gathers parent Q at the aligned guarded target-policy action.

Both modes use the immutable initialized parent in evaluation mode and transform n-step rows into fixed terminal targets before insertion. No generic replay-buffer or trainer schema change is required.

A new trainer-level bootstrap-action mode was rejected because it would broaden a simulator-only experiment into production RL contracts and allow target-network updates to change the supposedly frozen policy value.

### Bind target-action evidence separately from source transition identity

Existing source-transition identity remains backward compatible. Guard-aware mode will publish a separate canonical target-policy action identity plus counts of target actions, target guard replacements, nonterminal bootstrap rows, and the distribution of `raw max Q - guarded action Q`. The simulator-only checkpoint source binding and report config will include the bootstrap policy mode and evidence identity.

This avoids silently changing historical source identity semantics while still making the new labels auditable.

## Risks / Trade-offs

- [Target actions add parent inference and guard work on exploration rows] -> Reuse the deterministic parent result on parent rows and accept bounded extra work only for the registered simulator POC.
- [The deployment guard can select an action with lower parent Q than raw EndTurn] -> Record the non-negative raw-max Q gap; this is the intended evidence that the composite policy differs from the bare Q policy.
- [The action-per-turn cap is control state outside the network observation] -> Compute target actions with the same actual counter attached to each reached simulator state and bind forced-cap counts.
- [Guard-aware bootstrap could still fail to improve outcomes] -> The implementation grants no fitting or promotion authority; any fit requires a separate immutable two-arm registration and fresh cohorts.
- [New report fields can affect generated schemas] -> Bump runner report/checkpoint/manifest schema versions while retaining default values and focused compatibility tests.

## Migration Plan

1. Add RED regressions for epsilon-independent target action selection, trajectory alignment, guarded Q gathering, invalid-action failure, default compatibility, and evidence binding.
2. Implement the opt-in runner metadata and target transformation without changing default configuration.
3. Run focused LightSTS tests and strict OpenSpec validation only; do not run a fit in this change.
4. Roll back by removing the opt-in mode. Existing raw-greedy defaults and production artifacts require no migration.

## Open Questions

None for implementation. Horizon choice and any fit cohort are intentionally deferred to a separately registered experiment after this capability is complete.

