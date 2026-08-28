## Context

The fixed late safety policy currently asks whether the current state contains
a single-card lethal only when exactly one monster remains alive. The matched
live gate supplied two exact candidate/parent common states with multiple living
monsters where a guard-selected target-lethal attack was replaced by defense.
The larger regression used `Defend` instead of lethal `Bash+` against two
non-attacking Louses and incurred ten avoidable damage.

The completed guard action is available in `_apply_action_relative_candidate`,
but `_action_relative_candidate_veto_reason` currently receives only the
candidate and game. Existing combat damage and target helpers can evaluate both
actions without a simulator or model call.

## Goals / Non-Goals

**Goals:**

- Preserve a legal guard attack that kills its selected living target when the
  proposed candidate kills no living target.
- Cover multi-monster states and emit a stable traceable veto reason.
- Keep lethal-to-lethal and ordinary nonlethal candidate takeovers eligible.

**Non-Goals:**

- Estimate long-horizon value, choose a different target, or prove that every
  lethal action is globally optimal.
- Change the candidate artifact, threshold, registration schema, parent policy,
  or ordinary guard pipeline.
- Retrain, rerun the closed live cohort, launch the game, or promote a model.

## Decisions

1. Pass the completed guard action into the late safety predicate. This keeps
   the check relative to the behavior the candidate would replace. Reusing the
   existing state-only single-monster lethal check would either miss the live
   evidence again or suppress unrelated multi-target choices.
2. Add a deterministic helper that evaluates whether a `PlayCardAction` is an
   attack whose selected living target's effective HP is no greater than the
   action's estimated modified multi-hit damage. It will use the same card,
   target, weakness, vulnerability, block, and hit-count helpers as existing
   lethal guards.
3. Veto only when the guard is target-lethal and the candidate is not
   target-lethal. This preserves candidate freedom to substitute another lethal
   action and avoids turning the safety layer into an attack ranker.
4. Publish `mandatory_guard:target_lethal` through the existing resolution and
   trace path. No schema change is needed because veto reasons are already
   strings.

## Risks / Trade-offs

- [Damage estimation can be conservative or incomplete for unusual cards] ->
  reuse battle-tested helper functions and require an explicit legal target;
  uncertainty returns nonlethal rather than inventing a veto.
- [A target-lethal guard can be strategically worse than a setup action] -> the
  rule applies only to this experimental late candidate authority, and still
  allows lethal-to-lethal replacement.
- [Changing the safety function signature can break tests or callers] -> keep
  the guard action optional for direct compatibility and exercise both the
  outer-agent path and predicate-focused path.

Rollback removes the target-lethal predicate and mandatory check. Existing
candidate registration, artifact, and trace formats remain usable.
