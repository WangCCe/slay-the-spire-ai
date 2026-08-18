## Context

The simulator runner collects ordered one-step transitions but discards profile
identity before replay insertion. `DQNTrainerV2` uses one-step Double DQN with
`gamma=0.99`; the bounded smoke freezes the target network, so optimizer updates
cannot propagate newly observed terminal rewards backward through a trajectory.
The most recent 4,096-profile collection reached supported terminal outcomes
for all but two initialized profiles, making complete-trajectory targets
practical without changing the production trainer.

## Goals / Non-Goals

**Goals:**

- Preserve source profile identity and trajectory boundaries in simulator-only
  replay metadata.
- Add deterministic discounted episode returns as an opt-in target.
- Exclude incomplete trajectories rather than fabricate terminal rewards.
- Compare return targets with one-step targets on the same complete source rows.

**Non-Goals:**

- Change `DQNTrainerV2`, online production training, or checkpoint compatibility.
- Use truncated or unsupported trajectory prefixes for return targets.
- Promote the collision-free candidate that failed its registered technical
  gate, or authorize live gameplay from this experiment.

## Decisions

1. Retain `one-step-td` as the default target mode. Add
   `discounted-episode-return` only to the simulator runner, so production and
   existing reports remain unchanged unless explicitly registered.
2. Add `(seed, battle_index, decision_index)` analysis identity to collected
   transitions. Report a canonical source-transition hash so matched arms can
   prove they used the same state/action rows.
3. Add an independent complete-trajectory-only collection option. Both matched
   arms use it; incomplete profiles and all their prefixes are counted and
   excluded identically before target transformation.
4. For each supported terminal trajectory, compute backward returns
   `G_t = r_t + gamma * G_(t+1)`. Store `G_t` as the replay reward and mark the
   transformed row terminal so the unchanged trainer optimizes exactly that
   registered target without adding a second bootstrap term.
5. Bind target mode, gamma, source and target reward summaries, trajectory
   eligibility, exclusions, and source identity in report/checkpoint metadata.
   The fresh experiment uses the existing `0.99` discount and does not tune it.

Alternatives considered: updating the target network during the bounded run
would entangle propagation with update cadence; n-step TD would add a horizon
choice; full trainer changes would expand production risk. Complete-trajectory
returns are the smallest test of whether delayed credit is the limiting factor.

## Risks / Trade-offs

- [Return targets have higher variance and reflect the behavior policy] -> Keep
  the frozen parent anchor and require a matched one-step arm on identical rows.
- [Long trajectories can create larger target magnitudes] -> Bind target
  distributions and fail on non-finite values; do not add clipping in this
  experiment.
- [Complete-only filtering reduces data] -> Report excluded profile/transition
  counts and require every configured battle-index stratum to remain populated.
- [Marking every transformed row terminal changes trainer semantics] -> Scope
  it to the explicit simulator-only target mode and test that one-step replay is
  byte-for-byte unchanged by default.

## Migration Plan

Implement and verify the opt-in runner path, then register one fresh matched
experiment. A failed technical or policy gate retains `r4`; rollback is removal
or non-use of the opt-in flags because the default path is unchanged.

## Open Questions

None. The discount, cohort, training budget, and guardrails will be fixed before
outcome access.
