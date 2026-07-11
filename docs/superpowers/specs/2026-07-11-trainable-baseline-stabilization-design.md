# Trainable Baseline Stabilization Design

Date: 2026-07-11

This document records the approved direction for turning the current Ironclad agent into a trustworthy baseline before any new formal reinforcement-learning phase begins.

## Decision

Keep `slay-the-spire-ai` as the live runtime, test, trace, and evaluation repository. Use Bottled only as an offline policy teacher and comparator. Keep `sts_lightspeed` as an external mechanics and future rollout reference rather than replacing the live CommunicationMod integration.

The next phase is:

1. stabilize combat action arbitration;
2. prove the baseline through bounded fresh evaluation;
3. close repository and experiment hygiene gaps;
4. run a bounded combat-RL experiment against the frozen baseline;
5. leave formal non-combat RL behind a separate approval gate.

## Current Evidence

The latest completed 25-game evaluation reported:

- 0 victories;
- average floor 19 and maximum floor 33;
- 88 percent Act 1 boss reach rate;
- zero invalid CommunicationMod commands;
- 373 non-combat samples, including 363 complete samples and 216 matched live outcomes.

The final run in that batch produced stronger causal evidence than the remaining Bottled mismatches. At 3 HP against two slimes, the fallback planner found a two-card lethal sequence beginning with Hemokinesis. The takeover layer then treated Hemokinesis as ordinary pressure-unsafe HP loss, replaced it with `EndTurnAction`, and the player died with 2 energy remaining.

The failure is not a missing lethal detector. It is loss of lethal-plan provenance between the fallback planner and the combat guard layer.

## Goals

- Preserve a validated lethal plan through the action-arbitration layer.
- Keep hard safety vetoes for illegal actions and damage that kills the player before the lethal effect resolves.
- Prevent end-turn pressure heuristics from overriding a safe lethal prefix.
- Establish a repeatable promotion gate for a trainable combat baseline.
- Freeze and compare the baseline before any bounded combat-RL training run.
- Keep Bottled labels auxiliary so future RL can outperform rather than imitate Bottled.

## Non-Goals

- No formal non-combat RL training in this phase.
- No runtime dependency on Bottled or `sts_lightspeed`.
- No broad rewrite of `CombatRLAgent`, `OptimizedAgent`, or the combat simulator.
- No policy tuning justified only by a single Bottled disagreement.
- No requirement to achieve a victory before the baseline can enter a bounded training experiment. A real `victory=true` run remains the outer objective and a required reported metric.

## Alternatives Considered

### Continue mismatch-driven policy patches

This remains useful for repeated, outcome-backed differences, but current stable Bottled candidates are sparse and not clearly superior. Continuing it as the main loop would add more local rules without resolving guard conflicts.

### Start formal RL immediately

The data interfaces exist, but the live action layer still contains a causally demonstrated contradiction. Training now risks teaching the model around execution bugs and evaluating it through noisy run-level outcomes.

### Stabilize, freeze, then train

This is the selected approach. It retains the value of the current instrumentation and policy work while creating an explicit boundary between correctness fixes and learning experiments.

## Combat Guard Arbitration

Combat actions SHALL be arbitrated in this order:

1. Normalize the action and verify that its card, target, cost, and current screen state are executable.
2. Apply hard immediate-death vetoes, including card HP loss or reactive damage that kills the player before the action's lethal effect resolves.
3. Preserve an action that is the current prefix of a validated lethal plan.
4. Apply survival and encounter-mechanics guards when no safe validated lethal prefix exists.
5. Apply pressure, setup, and low-value-filler heuristics.
6. Fall back to a legal action or end the turn.

Low HP alone is diagnostic information. It SHALL NOT invalidate a deterministic lethal plan.

### Lethal-plan provenance

`IroncladCombatPlanner` already distinguishes the branch where `CombatEndingDetector` returns a non-empty lethal sequence. That decision SHALL be represented as plan metadata rather than inferred later from card names or damage estimates.

`OptimizedAgent` SHALL cache the plan kind with `current_action_sequence`, advance both through the same lifecycle, and clear the metadata whenever the sequence is cleared, replanned, or reset on a new turn.

`CombatRLAgent` SHALL ask the fallback agent whether the returned action belongs to the active validated lethal plan before applying pressure heuristics. The takeover layer SHALL not recompute an independent approximate lethal result.

### Safety boundary

A lethal prefix may still be rejected when the current action:

- is stale, unplayable, unaffordable, or has an invalid target;
- pays HP equal to or greater than current HP before dealing damage;
- triggers known reactive damage that kills the player before combat ends;
- no longer belongs to the active plan because the state forced a replan.

End-turn incoming damage is not a hard veto for a valid lethal prefix because that damage will not occur if the plan completes. Each subsequent action is checked again against the new live state.

## Data Flow

```text
Game state
  -> IroncladCombatPlanner
  -> validated action sequence + plan kind
  -> OptimizedAgent plan cache
  -> next fallback action + active plan provenance
  -> CombatRLAgent legality and immediate-death checks
  -> lethal-prefix pass-through or normal guard arbitration
  -> CommunicationMod action
```

Logs SHALL identify the plan kind, whether a hard veto fired, and whether a pressure heuristic was bypassed for a lethal prefix. They SHALL not claim that a sequence is validated merely because aggregate damage exceeds aggregate monster HP.

## Baseline Promotion Gate

Evaluation uses the production Windows Python and the existing conservative, no-training, 25-game fresh batch configuration.

A candidate baseline is promoted only after two consecutive fresh 25-game batches satisfy all of the following:

- zero invalid commands;
- zero uncaught gameplay exceptions attributable to the candidate;
- no unresolved A-class mechanics or guard-arbitration failure;
- every fresh sim-divergence cluster is classified, with no unresolved high-impact state mismatch;
- run metrics and death clusters are recorded in a committed summary report;
- focused tests and full pytest pass for every code change included in the candidate.

An A-class failure is a trace-supported, causally demonstrated error in mechanics, action legality, or action arbitration that can change the combat or run outcome. A plausible but unproven policy concern is diagnostic and does not justify a patch. When an A-class failure is found, fix one behavior class with a red regression, restart the two-batch count, and keep the commit scoped to that behavior.

## Repository Closure

Before the first training experiment:

- archive the completed Bottled oracle adapter change;
- replace placeholder Purpose text in affected current specs;
- resolve or explicitly defer stale active OpenSpec tasks;
- define report retention so summary Markdown and small regression fixtures are committed while large generated JSONL samples remain external or ignored;
- integrate the stabilized branch only after the promotion gate passes.

Existing untracked user artifacts SHALL not be deleted as part of this work.

## RL Entry Gate

After baseline promotion, freeze its commit and checkpoint. The first learning work is a bounded combat-RL experiment with:

- an explicit training game or step cap declared before launch;
- a fixed holdout seed pool evaluated before and after training;
- a separate fresh 25-game evaluation;
- the frozen baseline as the control;
- correctness gates identical to the baseline gate;
- no promotion based only on training reward.

The trained candidate is promoted only if it preserves correctness and improves at least one predeclared gameplay metric without a material regression in the others. Metrics include victory count, average floor, boss reach, Act 2 reach, and repeated death clusters.

Formal non-combat RL requires a later approved change. Bottled agreement may be used for behavior-cloning initialization, confidence weighting, or evaluation, but SHALL NOT be used as direct reward.

## Verification Strategy

The first implementation tranche uses:

1. a red regression reproducing the 3 HP, two-slime, Hemokinesis-plus-Headbutt lethal prefix;
2. control tests proving truly self-lethal HP costs remain blocked;
3. control tests proving reactive-damage self-kills remain blocked;
4. plan metadata lifecycle tests for replan, turn reset, and stale actions;
5. focused pytest for combat guard and planner tests;
6. full pytest with the repository temp-directory workaround;
7. one fresh 25-game batch, followed by a second only when the first has no A-class failure.

## Implementation Sequence

1. Complete the lethal-prefix regression and minimal provenance fix under `investigate-lethal-detection-failure`.
2. Run focused and full tests, then commit the behavior fix.
3. Run and report fresh evaluation batches until the two-batch gate passes or new A-class evidence appears.
4. Perform repository closure without deleting existing untracked artifacts.
5. Freeze the baseline and create a separate approved plan for the bounded combat-RL experiment.
