# Project Direction

Last updated: 2026-08-02

## Current Phase

The first real Ironclad A0 validation victory is a completed historical
milestone. Run `1780479519.run` reached floor 51 with `victory=true`; the
evidence is recorded in `reports/gameplay_validation_mechanics_audit.md`.

The bounded non-combat simulator-training smoke and its separately registered
policy-validity study are complete. The smoke-trained ranker retained a positive
signal against its seeded initialization but materially underperformed native
SimpleAgent on the untouched primary cohort. The current objective is therefore
to define a separate baseline-anchored warm-start stage before reconsidering
formal non-combat RL. Another pass of the same training, an enlarged cohort, an
isolated victory, or a healthy gameplay batch does not complete this phase.

## Training Boundary

Formal non-combat RL training is not currently authorized. A training go means
that state, action, reward/outcome, known-propensity evidence, and fixed offline
evaluation contracts are all reproducible and independently checkable. It
authorizes only a separately reviewed bounded training proposal. It does not
authorize live policy promotion.

Bottled-style decisions remain an auxiliary oracle for comparison, labels, and
diagnostics. They are not reward, ground truth, or a mandatory policy target.

## Current Blocker

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

The next authorized sequence is:

1. Preserve r1-r8, the completed r8 diagnosis/fix, and all external evidence
   byte-for-byte; do not prepare r9 or another replacement identity.
2. Preserve the smoke and policy-validity registrations, cohorts, models, and
   results as observed evidence; do not rerun or reuse them for selection.
3. Do not start formal RL from the current smoke or treat its positive interval
   against seeded initialization as evidence of policy competence.
4. Route the next stage through a separate OpenSpec change: preregister native
   SimpleAgent demonstrations, train a distinct warm-start ranker, and test
   baseline parity on an untouched cohort.
5. Treat SimpleAgent demonstrations as auxiliary supervision, not reward or
   permanent ground truth, and preserve the full candidate action space.
6. Keep Current and Bottled out of simulator training until a validated
   feature/action bridge exists; Bottled remains diagnostic evidence only.
7. Consider a bounded formal-RL proposal only after the warm-start policy
   demonstrates a credible baseline floor on untouched evidence.
8. Permit a later live replacement-qualification amendment only after a
   current, source-comparable feasibility audit demonstrates its planning gate.

## Work Lanes

The primary lane is non-combat RL readiness through a baseline-anchored
warm-start: establish simulator parity with native SimpleAgent on untouched
evidence before proposing formal RL, while keeping simulated and live evidence
separate.

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
