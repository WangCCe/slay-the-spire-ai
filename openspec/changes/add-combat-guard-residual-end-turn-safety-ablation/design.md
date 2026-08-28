## Context

The archived guard-advantage residual POC used a frozen post-guard model with
threshold 0.5. Its fresh paired gate failed 8 candidate-only wins versus 28
control-only wins, mean reward delta -1.75, and mean HP delta -0.88. Read-only
attribution found 261 residual `EndTurn` interventions across 191 profiles;
those profiles accounted for 3 candidate-only versus 19 control-only wins and
large negative reward and HP deltas. Profiles without that intervention were
near neutral, but that subgroup is observational because policy trajectories
had already diverged.

## Goals / Non-Goals

**Goals:**

- Causally test whether forbidding the post-guard residual from reversing the
  guard back to `EndTurn` removes the observed outcome regression.
- Compare guarded control, unrestricted residual, and masked residual on one
  fresh matched cohort with one fixed recipe.
- Preserve exact abstention, legal action masking, full decision traces, and
  development-only authority.

**Non-Goals:**

- Retrain the residual or change its threshold, architecture, labels, corpus,
  parent, guard, reward, or action representation.
- Test additional forbidden actions or intervention-rate limits in this
  change.
- Start the game or CommunicationMod, load a production checkpoint, or grant
  gameplay, qualification, or promotion authority.

## Decisions

### Exclude EndTurn before residual selection

The masked arm SHALL remove RL action 90 from the canonical alternative mask
after the guard proxy has replaced raw parent `EndTurn`. If no distinct masked
alternative remains, the policy SHALL abstain to the exact guard action and
record the safety skip. The gate still sees the same frozen parent features,
guard action, and full legal mask; only the residual action candidate set
changes.

Alternative considered: let the model choose `EndTurn` and overwrite it after
selection. Rejected because telemetry would claim an open intervention while
execution silently abstained, obscuring the causal mechanism and latency.

### Use one fresh three-arm matched cohort

The evaluation SHALL use seed-disjoint profiles not present in corpus fitting
or the previous gate. All three arms use identical seeds, battle indices,
parent, guard, native module, item metadata, decision bounds, and residual
artifact. The unrestricted arm reproduces the original behavior on the new
cohort; the masked arm differs only by the EndTurn alternative exclusion.

Alternative considered: reclassify the previous cohort after deleting its
EndTurn traces. Rejected because later state trajectories would differ and the
result would not be causal.

### Require both control-relative safety and direct ablation improvement

The masked arm is promising only when the unrestricted arm expresses at least
one residual EndTurn treatment opportunity, the masked arm independently passes
the existing five control-relative policy conditions, executes no residual
EndTurn action, has no nonterminal direct-ablation exclusions, and is
non-regressive versus the unrestricted residual on matched-only wins, mean
reward, and mean HP. Any failure closes this hypothesis without another mask,
threshold, seed, or training run.

Alternative considered: retain the masked arm if it merely improves over the
failed unrestricted arm. Rejected because a less harmful policy can still be
worse than guarded r16.

## Risks / Trade-offs

- [EndTurn may sometimes be the genuinely best action] -> Treat the mask as a
  safety ablation limited to the wasteful-EndTurn guard context, not a global
  action prohibition.
- [Fresh cohort variance may change the unrestricted baseline] -> Compare all
  three arms on identical profiles and publish both paired contrasts.
- [Other high-frequency interventions may still regress] -> Require the masked
  arm to pass the full original gate; do not add post-hoc filters here.
- [Simulator-only success may exploit divergence] -> Retain development-only
  authority and require a separate divergence-calibration change before any
  game run.

## Migration Plan

No production migration occurs. Implement the optional evaluation-only mask,
run the fixed three-arm gate, publish the result, and archive the change. A
rollback removes the offline runner, tests, and reports; r16 and gameplay remain
unchanged.

## Open Questions

No open parameter may be answered after seeing the registered cohort. A future
change may replace multiclass targets with action-relative value learning only
after this action-safety hypothesis is closed.
