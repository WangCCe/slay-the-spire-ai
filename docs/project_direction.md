# Project Direction

Last updated: 2026-08-02

## Current Phase

The first real Ironclad A0 validation victory is a completed historical
milestone. Run `1780479519.run` reached floor 51 with `victory=true`; the
evidence is recorded in `reports/gameplay_validation_mechanics_audit.md`.

The bounded simulator-training smoke, policy-validity study, and separate
baseline-anchored supervised warm-start study are complete. The warm-start
primary and replay matched, but validation failed both the registered overall
teacher-fit threshold and the primary rollout floor gate. Final-test seeds were
therefore untouched. The read-only failure audit is now complete: forced
single-candidate rows inflated headline agreement, and the policy diverged on
teacher states near the start of every validation run.

The subsequent train-only structured baseline-ranker POC is also complete. Its
primary/replay execution identity matched, but the candidate missed every
aggregate selection gate: multi-candidate agreement fell from `70.00%` to
`67.82%`, macro agreement fell by `7.89` points, and cross entropy worsened by
`0.1924`. Route improved by `11.00` points in all four folds and card reward by
`2.32` points overall, while event and shop regressed; the shop head predicted
`leave` on all 124 held-out decisions. No model was selected and all authority
remains false.

The terminal legacy-preserving route/card residual POC is now complete and is
also a deterministic valid negative. Event/shop delegated exactly on 268 rows,
the legacy base remained immutable, and replay matched, but card agreement did
not change and route improved by only one net decision out of 300. Overall
agreement delta was `+0.001149`, route delta `+0.003333`, and fold 1 regressed.
No model was selected. Baseline-imitation model trials on this corpus are now
closed. The first registered read-only state/action and SimpleAgent
teacher-suitability audit failed closed before publication because its timed
body exceeded the fixed 120-second limit. A separately registered,
byte-equivalent runtime recovery then completed in 34.938 seconds and strictly
recomputed every canonical artifact. It reconstructed 993/993 teacher actions,
found no raw-adapter gap or observed representation conflict on 602
multi-candidate rows, and failed all six fixed teacher-suitability checks. The
terminal verdict is `simpleagent_unsuitable_as_policy_quality_gate`.

SimpleAgent is therefore closed as a policy-quality target and retained only as
an auxiliary regression oracle. The current objective is a separate read-only
`outcome-backed-noncombat-rl-readiness` go/no-go audit, not another imitation
POC, fresh simulator study, or formal non-combat RL training.

## Training Boundary

Formal non-combat RL training is not currently authorized. A training go means
that state, action, reward/outcome, known-propensity evidence, and fixed offline
evaluation contracts are all reproducible and independently checkable. It
authorizes only a separately reviewed bounded training proposal. It does not
authorize live policy promotion.

Bottled-style decisions remain an auxiliary oracle for comparison, labels, and
diagnostics. They are not reward, ground truth, or a mandatory policy target.

## Current Blocker

State/action source closure is no longer the primary blocker: the recovered
teacher audit proved exact reconstruction and adequate raw-adapter visibility
on the preserved train corpus. The remaining training blocker is outcome-backed
readiness: known-propensity support, reward/outcome attribution, untouched
offline evaluation, and a preregistered training/promotion boundary are not yet
jointly demonstrated.

The active v2 known-propensity outcome-evidence study is stopped before any
replacement qualification or study start. R7 remains immutable and retired
after `source_validation_failed`; its raw-first source fix, focused
regressions, registered commit gate, and OpenSpec archive are complete.

The separately reviewed r8 replacement reached `source_verified`, then failed
at `request_validation_failed` before active request publication, gameplay, or
trajectory collection. The immutable chain proves at least one live boundary;
the same-session operator journal records one issued invocation but does not
independently prove the exact count. Its standalone verifier and independent
closeout passed, CommunicationMod and protected inventories were restored
exactly, target processes are zero, and the registered study root remains
absent. R8 is consumed and permanently retired; it cannot be retried or used
to prepare r9 under its amendment.

The separate regression-backed diagnosis proved that the r8 qualifier CLI
bound `--request` to the absent active publication path instead of the reviewed
repository `request_source_path`. The narrow source fix adds one canonical
builder and exact validator for that suffix, routes the production-Python smoke
through it, and preserves every retired r8 artifact unchanged.

The offline feasibility audit now binds the frozen B3-B7 readiness evidence
and current v2 registration exactly. It observes 125 complete trajectories,
one raw victory, and zero deterministic-Current-supported victories because
the winning trajectory has exact target weight zero. For 600 attempts to have
an 80% plug-in probability of reaching the registered three-supported-victory
gate, the supported-victory rate would need to be about 0.7118%. The current
audit is `not_demonstrated` because the evidence is historical-only, contains
no supported victory, and yields zero plug-in pass probability. It grants no
qualification, study, gameplay, OPE, training, or promotion authority.

The offline `sts_lightspeed` adapter POC now binds the simulator checkout,
submodule commits, physical source hash, adapter commit/source hash, and native
module hash. Two independent 20-seed batches were identical, terminated on all
seeds, covered route/shop/event/card-reward decisions, and applied all 46
inspected candidates on isolated clones. The historical-prefix check matched
12/12 early reward candidate sets from six recent real runs. The fit verdict is
`adapter_poc_ready`.

That verdict establishes an offline environment interface, not policy quality
or mechanics parity. The declared first-candidate baseline won 0/20 runs,
battle potion use is disabled, non-target screens remain baseline-controlled,
and arbitrary live non-combat states cannot be imported. Simulator transitions
remain separate from live known-propensity, OPE, and supported-outcome evidence.
Every live, training, OPE, qualification, and promotion authority flag remains
false.

The first learning integration then repaired three environment-contract defects:
clones now deep-copy the map across Act transitions, event snapshots omit
undefined upstream HP fields, and new environments canonicalize the initial
encounter field. The native adapter is loaded before PyTorch on Windows. A new
fit audit bound to adapter commit `68369db646a074fa712fccddc6a650015197332d`
again returned `adapter_poc_ready` with the same 20-seed and historical-prefix
checks.

The registered bounded smoke used 32 train seeds over four passes, 64 disjoint
paired holdout seeds, and one identical replay. Both executions stayed below
their 600-second bounds and matched canonically. The trained greedy policy
improved mean terminal floor by `2.921875`; its pre-registered 95% paired
bootstrap interval was `[1.703125, 4.171875]`. Of 64 pairs, 29 improved, 30 were
unchanged, and five declined. Both initial and trained policies still won 0/64
holdout runs. The verdict is `pipeline_demonstrated_with_holdout_signal`, with
all downstream authority false.

Adapter API v2 then exposed the upstream SimpleAgent's target action as exactly
one current candidate on a baseline-following trajectory. The r3 fit bound
adapter commit `a810d6d0ce92c1ebab8483fb8819163fc76d54fe` and checked 770 native
target decisions across seeds `0..19` twice with four-category coverage,
non-mutation, terminal outcomes, and 12/12 historical-prefix agreement.

The registered policy-validity study used compatibility seeds `2000..2003` and
fresh seeds `3000..3063`. Its primary and identical replay matched canonically.
The trained policy averaged floor `14.5625`, seeded initial `11.796875`, and
native SimpleAgent `19.96875`; all recorded 0/64 victories. Trained minus
SimpleAgent was `-5.40625`, with registered 95% interval
`[-7.875, -2.921875]`. Trained minus initial remained positive at `+2.765625`,
with interval `[1.375, 4.25]`. The structurally valid verdict is
`study_valid_without_baseline_signal`, and all downstream authority remains
false.

The registered baseline warm-start then used train seeds `4000..4031` and
validation seeds `5000..5015`. Primary and replay matched canonically. The
candidate reached 0.790071 overall and 0.786065 macro teacher agreement, with
per-category agreement of 0.640000 card reward, 0.927536 event, 0.845953 route,
and 0.730769 shop. It averaged floor 20.0 against SimpleAgent's 24.6875; the
paired mean difference was `-4.6875` and its 95% interval was
`[-11.6890625, 2.5]`. Both policies won 1/16. Validation failed, final-test
seeds `6000..6031` remained untouched, and the valid negative verdict is
`study_valid_without_baseline_floor`. All downstream authority remains false.

The post-study read-only audit aligned all 16 candidate/SimpleAgent action
prefixes. Every run diverged by floor 3, 13 within five target decisions, led
by eight route and seven card-reward decisions. Validation agreement on the
471 rows with more than one legal action was only 68.58%; route fell from its
84.60% headline to 65.09% after forced rows were removed. Frozen-model train
multi-choice agreement was 76.32%, so the evidence points first to
representation/teacher-state competence, with rollout state shift and unseen
labels as secondary risks. The full analysis is in
`reports/noncombat_simulator_baseline_warm_start_failure_audit_20260802.md`.

The next authorized sequence is:

1. Preserve r1-r8, the completed r8 diagnosis/fix, and all external evidence
   byte-for-byte; do not prepare r9 or another replacement identity.
2. Preserve the smoke and policy-validity registrations, cohorts, models, and
   results as observed evidence; do not rerun or reuse them for selection.
3. Do not start formal RL from the current smoke or treat its positive interval
   against seeded initialization as evidence of policy competence.
4. Preserve the completed warm-start registration, model, artifacts, negative
   verdict, and untouched final cohort; do not tune or rerun this study.
5. Preserve the completed read-only first-divergence/floor-deficit audit; do
   not reuse its validation rows for model selection.
6. Preserve the completed structured-ranker POC and valid negative verdict.
   Do not rerun it, change its thresholds, or advance its unified candidate to
   fresh simulator evidence.
7. Treat SimpleAgent as temporary auxiliary supervision, preserve the full
   candidate action space, and keep Current/Bottled out of simulator training
   until their feature/action bridges are validated.
8. Preserve the completed route/card residual POC, its registration, canonical
   artifacts, and valid negative verdict. Do not tune, rerun, or attempt a third
   model on the observed train corpus.
9. Preserve both consumed teacher-sufficiency registrations, the v1 timeout,
   and the strictly recomputed r2 result. Do not retry either registration or
   treat zero observed representation conflicts as policy-quality evidence.
10. Route the next capability through a separate read-only outcome-backed
   non-combat RL readiness audit. Consider bounded formal RL only after it
   proves reproducible state/action, support, reward/outcome, and untouched
   evaluation contracts and a separate training OpenSpec is approved. Permit
   later live work only through existing crash/qualification gates.

## Work Lanes

The primary lane is a separate read-only outcome-backed non-combat RL readiness
audit. It should consume only frozen evidence and determine whether state/action
coverage, known-propensity support, terminal outcomes, reward attribution, and
untouched offline evaluation are sufficient to preregister a bounded training
study. It must define an explicit go/no-go verdict without fitting a model,
spending fresh simulator cohorts, launching gameplay, or granting training or
promotion authority. Simulated and live evidence remain separate.

Live gameplay is a maintenance and registered-evaluation lane only. Launch it
for a crash, stuck state, repeated A-class simulator/mechanics defect, or an
explicitly registered RL qualification/evaluation gate. Do not run automatic
five-game batches merely to search for another heuristic patch.

Defer broad strategy tuning, Bottled-driven live behavior, reward redesign,
formal training, and live promotion until their evidence gates and separate
OpenSpec changes authorize them.

## Engineering Rules

- Route proposal, contract, or capability work through repository OpenSpec.
- Begin with read-only evidence; require a failing regression before a behavior
  fix.
- Use focused pytest and the repository test gates. Do not substitute an
  unregistered raw full-suite run for the commit gate.
- Keep changes cohesive and preserve unrelated local artifacts.
- Stop when evidence is ambiguous rather than tuning around it.

Historical reports and archived changes retain the objectives and authority
boundaries that applied when they were written. This document is the canonical
source for the current project phase.
