## Context

The latent-gated development adapter is not an RL v2 checkpoint. It wraps the
frozen production-r16 network, predicts a correction action and a gate score,
and selects the correction only above threshold. The r3 live-shadow cohort
proved exact parent parity, legal candidate actions, zero errors, and bounded
latency, but intentionally returned the parent action. An active evaluation
must preserve the same artifact and parent identities while giving the selected
candidate proposal authority before the existing `CombatRLAgent` guards.

## Goals / Non-Goals

**Goals:**

- Add explicit, opt-in, eval-only candidate takeover with complete provenance.
- Preserve the production parent, state/action encoders, outer guards, noncombat
  policy, and final-action callback path.
- Produce enough trace and run evidence for one ten-pair matched decision.
- Restore production configuration exactly and keep promotion separate.

**Non-Goals:**

- Online training, fitting, threshold changes, alternate candidates, or
  same-cohort tuning.
- Repackaging the adapter as a normal production checkpoint.
- Bypassing existing energy, legality, card-selection, or fallback guards.
- Claiming a win-rate effect from ten pairs.

## Decisions

### Candidate mode is a separate opt-in runtime

Add `STS_COMBAT_RL_LATENT_CANDIDATE_REGISTRATION` and a matching batch-wrapper
argument. It is mutually exclusive with the shadow registration. The shared
registration parser accepts an explicit expected mode, so old `mode=shadow`
registrations remain behavior-neutral and a new `mode=candidate` registration
cannot be loaded accidentally through the shadow environment variable.

The candidate runtime reuses the already validated adapter inference and trace
machinery. RL v2 first computes the frozen-parent greedy action. Candidate mode
then verifies parent parity and legality, selects the adapter action only when
the gate is open, and decodes that selected proposal. The surrounding combat
agent continues to apply its ordinary guards and calls the existing final-action
commit callback.

### Runtime errors invalidate evidence without destabilizing gameplay

Candidate initialization fails before gameplay unless training is disabled,
epsilon is exactly zero, expert mix is disabled, the active parent checkpoint
and state dict match, and all source/artifact hashes match. A proposal or commit
error disables candidate takeover and records an error event; the parent action
is used only to keep the game recoverable. Any such event invalidates the arm,
so a partially parent-controlled arm cannot qualify.

Decision events add selected action, takeover-applied, and selected-matches-final
fields to the existing parent/correction/candidate/final evidence. Transient
`WaitAction` callbacks remain separately audited and do not consume the policy
decision budget.

### The first gate is small and promotion-neutral

Use ten fresh Ironclad A0 seeds, candidate arm first and r16 parent arm second,
with conservative routing, eval mode, epsilon zero, and identical seed order.
The candidate registration fixes a decision budget large enough for all ten
games. Candidate and parent runs, `.run` records, decision traces,
`ai_debug.log`, and CommunicationMod errors are reconciled. A native crash may
receive at most one same-config recovery before the arm's first completed game;
policy/runtime validation failures are not retried.

The candidate qualifies only when it wins more paired floors than r16, at least
one pair is non-tied, total floors and Act 2/Act 2 boss/Act 3 progression are
non-worse, victories are non-worse, all games and seeds match, candidate
takeover occurred, and all runtime checks pass. All ties or any failed condition
retain r16. Passing allows only a separate promotion decision.

## Risks / Trade-offs

- [The candidate may interact badly with outer guards] -> Trace selected and
  final actions separately and require legal final actions and zero errors.
- [Ten pairs have low statistical power] -> Use them as a bounded go/no-go
  canary, not a win-rate estimate; require strict paired non-regression.
- [Sequential arms can see machine-state drift] -> Freeze configs and seed
  order, restore production between arms, and reconcile runtime health.
- [An opt-in environment variable could leak] -> The batch wrapper clears both
  latent runtime variables by default and production restoration is hash-checked.

## Migration Plan

1. Add RED registration, routing, trace, mutual-exclusion, and batch-env tests.
2. Implement candidate mode and validate focused plus commit gates.
3. Commit/push the source, then add a source-bound registration, seed pool, and
   immutable candidate/parent launch configs.
4. Run candidate and parent arms once, restore production after each, reconcile
   evidence, and publish the fixed decision.
5. Roll back by clearing the candidate registration variable and restoring the
   saved production configuration; do not modify the r16 checkpoint.

## Open Questions

None. A passing gate still requires a separate explicit promotion change.
