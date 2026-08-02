## Context

The formal-RL readiness audit accepts a reward domain only when a separate
`noncombat-formal-rl-reward-contract-v1` artifact is present and tested. The
repository currently has two related but intentionally weaker contracts:

- live/OPE evidence preserves terminal victory and floor reached as separate
  channels and forbids floor variation from replacing victory truth;
- the bounded simulator smoke uses non-negative floor advancement divided by
  57 plus a terminal victory bonus of 1.0, explicitly for pipeline testing.

The smoke formula is useful shaping evidence but is not a formal objective.
Its scalar weight was fixed to bound a smoke, not selected or proved to make
victory strictly primary for every future environment. The new contract must
close that semantic gap without changing runtime reward code or running a
training experiment.

## Goals / Non-Goals

**Goals:**

- Define a versioned primary victory channel and bounded secondary floor
  progress channel.
- Make the permitted optimization relationship mathematically explicit.
- Prove fixed formula examples, bounds, terminal semantics, exclusions, and
  simulator/live provenance in a deterministic artifact.
- Feed that artifact into a new immutable readiness registration and verify
  that only the reward domain changes from blocked to passed.

**Non-Goals:**

- Choose or tune a production reward weight, optimizer, model, or algorithm.
- Modify the existing simulator smoke reward or claim it is formal-RL-ready.
- Blend floor reached into live/OPE victory truth.
- Run gameplay, simulator rollouts, native code, model fitting, or training.
- Resolve the credible baseline-floor or target-supported-outcome blockers.

## Decisions

### Represent the formal objective as ordered channels

The canonical contract will expose:

1. `terminal_victory`, a boolean terminal channel and the primary objective;
2. `floor_progress`, a simulator-only potential-shaping channel whose complete
   episode contribution is bounded to `[0, 1]`.

The floor channel uses the existing audited transform: cap source and successor
floors to `[0, 57]`, pay only non-negative advancement, and divide by 57. With
discount 1.0, monotone advancement telescopes and cannot contribute more than
1.0 over an episode. Regressions, repeated floors, HP, gold, deck state, labels,
and non-terminal victory-looking fields pay nothing.

This retains the tested pipeline transform while separating it from the
terminal objective. Defining one unconstrained scalar reward was rejected
because it would hide the required priority relationship.

### Permit only lexicographic or strictly dominant scalarization

The contract allows two future implementation classes:

- lexicographic optimization with terminal victory first and floor progress
  second; or
- a scalarization whose terminal-victory weight is strictly greater than the
  registered maximum complete-episode shaping contribution.

The contract records the smoke's `victory_bonus=1.0` as not automatically
formal-compatible because equality is not the required strict inequality. No
replacement numeric weight is selected by this change. A later training
proposal must bind its exact mode and prove conformance.

### Keep live outcomes and simulator shaping separate

For live/OPE evidence, terminal victory remains the primary outcome and floor
reached remains a separate diagnostic channel. Floor potential is permitted
only for simulator training under explicit simulator provenance. A future
cross-source training proposal must separately define divergence controls and
real-game evaluation.

Current, Bottled, SimpleAgent, teacher agreement, HP, gold, deck heuristics,
behavior propensities, and OPE estimates are explicit exclusions from reward.
They may remain diagnostics or auxiliary labels under their existing contracts.

### Build one registered deterministic artifact

A small offline module will consume a versioned registration that hash-binds:

- its committed implementation and focused tests;
- the simulator smoke reward implementation and tests;
- the live/OPE, decision-loop, simulator-smoke, and readiness specs;
- the completed readiness manifest and report.

It will publish `configuration.json`, `contract.json`, `verification.json`,
`report.md`, and `artifact_manifest.json`. Verification will execute fixed
in-memory formula examples and contract invariants only. Publication uses
temporary files with manifest-last atomic installation; strict validation
recomputes every canonical byte.

This is preferred over hand-authoring a JSON declaration because source and
test drift would otherwise be invisible. A general reward framework was
rejected as unnecessary before a training proposal exists.

### Re-register, never mutate, the readiness audit

The 2026-08-02 readiness registration and report remain immutable. After the
reward implementation is committed and its artifact verifies, this change will
create one new readiness registration with the formal contract binding filled.
The expected delta is fixed before execution:

- reward: blocked -> passed;
- state/action, reference isolation, evaluation: remain passed;
- baseline policy, outcome support: remain blocked;
- overall verdict: remains `not_ready_for_bounded_training_proposal`;
- every execution and promotion authority: remains false.

Any other domain or verdict change fails the handoff rather than being
interpreted after the fact.

## Risks / Trade-offs

- [Risk] Ordered channels may not map directly to a future RL library.
  -> Mitigation: permit a proved strictly dominant scalarization, but require a
  later proposal to bind the exact implementation.
- [Risk] Floor progress can still incentivize simulator-specific behavior.
  -> Mitigation: restrict it to simulator provenance and retain separate
  simulator-divergence and real-game evaluation gates.
- [Risk] A contract test can prove semantics but not policy quality.
  -> Mitigation: reward readiness is one independent domain; baseline and
  outcome blockers remain closed.
- [Risk] Re-running readiness could be mistaken for new policy evidence.
  -> Mitigation: bind the same frozen component evidence plus only the new
  contract and require the preregistered one-domain delta.

## Migration Plan

1. Implement the contract builder/validator and focused tests.
2. Commit them and freeze one source-bound registration.
3. Publish and strictly recompute the formal reward contract.
4. Create one new readiness registration containing the contract binding,
   publish it, and compare its matrix with the immutable prior matrix.
5. Update project direction, sync specs, archive, run the commit gate, commit,
   and push.

Rollback removes only this change, the reward module/tests/artifacts, and the
new readiness registration/report. The prior readiness audit and all runtime
reward behavior remain unchanged.

## Open Questions

None. Exact scalarization, algorithms, and training execution belong to a
later bounded-training proposal after every readiness domain passes.
