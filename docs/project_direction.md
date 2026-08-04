# Project Direction

Last updated: 2026-08-04

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
an auxiliary regression oracle. The separate formal-RL readiness audit and its
formal-reward r2 handoff are complete and strictly recomputed. State/action,
reference isolation, formal reward, and evaluation now pass; baseline policy
and outcome support remain blocked. The terminal verdict remains
`not_ready_for_bounded_training_proposal`, with all execution and promotion
authority false.

The bounded simulator-only non-combat RL experiment completed its one
authorized logical execution as `experiment_blocked`. Static preflight matched
the pushed source, runtime, native-module bytes, physical simulator source,
registration, and authorization, but Windows failed to load the bound native
module with `ImportError: DLL load failed ... The specified procedure could not
be found.`. The run stopped before constructing an environment: it consumed
zero registered episodes,
performed zero optimizer updates, and left prefix replay, canary, and holdout
untouched. Cumulative charged wall time was `0.21622760000173002` seconds. The
standalone standard-library verifier accepted all 174 terminal checks, and the
focused publication/verifier regression passed 18 tests. The logical execution
is terminal and cannot be retried, repaired in place, retuned, or reinterpreted
as learning evidence. Formal readiness remains
`not_ready_for_bounded_training_proposal`; all Current, live, OPE, causal,
qualification, loading, formal-RL, and promotion authorities remain false.

The subsequent read-only loadability audit identified the exact process-global
runtime collision. The runner import path and source-only preflight imported
PyTorch first, which loaded Conda's old `libwinpthread-1.dll`; CLion's newer
`libstdc++-6.dll` then required the absent `clock_gettime64` and `nanosleep64`
exports. A source-only repair now lazily imports policy-model Torch symbols,
reads the Torch version from distribution metadata, loads and validates native
before initializing Torch, and creates fresh output only after the pristine CPU
runtime is ready. Pre-start failure therefore leaves output absent, while
resume validation failure preserves the last complete evidence; the existing
one-shot and terminal rules still apply after the started journal. This repair
does not alter or reopen r1 and grants no successor registration, seed,
execution, training, live, qualification, loading, or promotion authority.

The separately reviewed r2 preregistration now records an explicit decision to
reuse the untouched `50000..51663` cohort. A current-tree structured scan found
two intersecting physical registration files, both byte-identical copies of the
same terminal r1 registration, and no second logical overlap. The canonical
reuse inventory (`9664d6961fcb6e713e0f537bc212953b4a0a62236cc3ab015f12036877ea96bd`)
binds r1's verified zero-environment, zero-seed, zero-episode, and zero-update
evidence. The all-false r2 registration
(`8e0576bbf86b2334ccce67ac809410a02dcbfa6419f075211bbe48d0164f8549`)
binds repaired source `8d123fdf32bd94bc29e53a97f217a2b7ca40c4fe`, the unchanged native and
simulator identities, and the fixed experiment contract. Proposed identity
`noncombat-simulator-rl-20260804-r2`, its authorization file, and output remain
non-executable and absent. A later exact authorization must be committed and
pushed before the runner's full source-only preflight can execute.

The first source-bound Current-policy simulator bridge registration remains a
valid negative. Its event row stopped on missing semantics. The source-bound r2
successor now resolves the exact `Liars Game` `Agree`/`Disagree` contract and
proves the original four rows and all execution settings unchanged. All four
Stage 1 rows pass deterministically, so the verdict is now
`frozen_bridge_structurally_compatible`.

The single authorized reused-seed Stage 2 check then executed and failed closed
at the first unsupported event identity, `The Cleric`. Native module, build,
simulator, source, and submodule identities all matched. This is a semantic
coverage blocker, not a policy-quality result, and those seeds remain consumed.

The subsequent hash-bound static audit, total observation contract, and
reachable-surface successor now close all 48 simulator-reachable Ironclad A0
event-option targets. Historical API v2 evidence remains explicitly readable;
new modules and bridge sessions use API v3.

Two separately preregistered API v3 own-trajectory cohorts were then consumed
as valid structural negatives before completing one seed row. The first stopped
on missing `Scrap Ooze` semantics. After the complete reachable-event repair,
the successor stopped on the post-removal shop `remove_cost == -1` sentinel.
Neither result is retryable or retroactively positive.

The remove sentinel, sold shop inventory, and remaining shop domain have since
received source-bound audits and narrow repairs. The current successor module
filters sold slots, fails closed on Courier restock semantics, and removes
impossible Sozu/full-capacity potion purchases while preserving visible
inventory. These changes close known evidence corruption paths but still do not
provide a completed Current own-trajectory row.

The baseline-floor readiness audit returned `diagnostic_smoke_required`.
Current is the only eligible non-teacher baseline candidate; SimpleAgent and
Bottled remain auxiliary, and all learned imitation/structured/residual lanes
remain valid negatives. It required a separately reviewed
reused-development-seed Current bridge smoke with structural-only authority
before another untouched compatibility or quality cohort.

That reused-development-seed smoke has now executed exactly once and finalized
as `current_bridge_diagnostic_failed` before retaining its first row. The
runner accessed a non-contractual native candidate field, `action_type`; the
production candidate schema does not provide it, while the fake regression
candidate did. This is a runner-contract defect rather than simulator or policy
evidence. The attempt is consumed and will not be repaired or rerun.

The separate offline candidate-schema fix is now complete. Its shared fake
candidate uses exactly the production validated fields, the runner no longer
reads candidate-side `action_type`, and missing, empty, or non-string Current
evaluation action metadata fails before `step()`. The fix recomputes the
consumed canonical output without native loading and leaves every consumed
evidence byte unchanged. It did not construct an environment or consume a seed,
and it does not reopen or replace the failed attempt.

The subsequent read-only anti-retry review finds one separately preregistered
successor diagnostic eligible for proposal. The consumed identity and failure
remain terminal; the allowed successor must use a new identity, the same four
reused development seeds and fixed controls, an exact lineage to the completed
schema fix, and one-shot fail-closed authority. This review authorizes planning
only. It does not authorize native loading, environment construction, execution,
a readiness refresh, or any training or promotion surface.

That successor r2 diagnostic was later consumed as a second zero-row failure on
`potion_metadata_missing`. The closed potion and relic identity repairs and the
production candidate-schema repair then supported one separately preregistered
post-repair Current baseline study. Its one authorized attempt retained 18
replay-identical policy rows for canary seeds `11000..11008`, then terminated as
`study_blocked` on `card_metadata_cost_invalid` with detail `Injury`. The full
canary was not completed, bootstrap did not run, and holdout seeds
`12000..12063` remained untouched. This is a terminal blocked result, not a
baseline-floor result, and it cannot be retried or replaced.

A separate read-only cost-domain audit then proved a closed exporter/bridge
representation mismatch: exactly 20 stable native IDs have empty metadata cost
and a leading `Unplayable.` description, while three Wish option identities
have empty cost without that contract. The completed offline repair now maps
only the exact 20 audited identity and metadata shapes to SpireComm cost `-2`
and keeps every drift or unlisted empty-cost record fail closed. This removes a
known future bridge compatibility defect but does not reopen the consumed
study, establish a baseline floor, or change formal-RL readiness.

## Training Boundary

Formal non-combat RL training is not currently authorized. A training go means
that state, action, reward/outcome, known-propensity evidence, and fixed offline
evaluation contracts are all reproducible and independently checkable. It
authorizes only a separately reviewed bounded training proposal. It does not
authorize live policy promotion.

Bottled-style decisions remain an auxiliary oracle for comparison, labels, and
diagnostics. They are not reward, ground truth, or a mandatory policy target.

## Current Blocker

State/action source closure, formal reward, and evaluation isolation are no
longer primary blockers. The source-bound reward contract keeps terminal
victory primary, floor progress secondary and simulator-only, reference labels
excluded, and all authority false. Its readiness r2 handoff changed only the
reward domain from blocked to passed. The remaining blockers are an
undemonstrated credible baseline floor and source-incomparable evidence with
zero target-supported victories. The next prerequisite is the non-teacher
baseline floor; passing it would not override the outcome blocker or authorize
training.

The immediate baseline-lane blocker is now the terminal post-repair study
result. Eighteen partial canary rows do not satisfy the 32-row canary contract,
and their partial floors cannot be promoted into quality evidence. Current
structural closure and a credible baseline floor therefore remain
undemonstrated. The observed `Injury` empty-cost metadata boundary is a narrow
offline compatibility candidate only; repairing it later would not reinterpret
or reopen the consumed study.

All formal-RL authority remains false. Source comparability with zero
target-supported victories remains an independent blocker, unchanged by the
simulator-only partial rows. No training proposal may be considered while
either baseline policy or outcome support remains blocked.

Any future baseline-floor study must retain every selected episode. A declared
support blocker counts conservatively as a non-victory at the last supported
floor, remains in paired and aggregate denominators, and is reported by exact
reason, seed, count, and rate. Dropping unsupported episodes would create
policy-dependent survivor bias and cannot authorize a positive floor.

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
10. Preserve both completed formal-RL readiness registrations, the formal
    reward contract, and the baseline-floor readiness audit byte-for-byte.
    Current is the only eligible non-teacher candidate, but its floor remains
    undemonstrated. Keep target-supported outcomes separate and consider bounded
    formal RL only after every domain passes and a separate training OpenSpec is
    approved.
11. Preserve both Current bridge registrations, both consumed API v3
    compatibility cohorts, and seeds `2000..2003`, `7000..7007`, and
    `7100..7107`. Do not retry or reinterpret any of them after repairs.
12. Preserve the consumed Current bridge diagnostic registration, finalized
    zero-row failure, and canonical artifacts. Do not repair, resume, replace,
    rerun, or reinterpret that attempt.
13. Preserve the completed offline candidate-schema fix and its production-key
    regression. It grants no replacement execution or readiness authority. Any
    later diagnostic attempt requires separate preregistration and explicit
    anti-retry review. A later floor proposal must still fix comparison,
    numeric gates, unsupported-rate ceiling, bootstrap, stop, and holdout
    contracts.
14. Treat the completed anti-retry review as permission to propose exactly one
    new versioned successor diagnostic, not to rerun or replace the consumed
    identity. Require a narrow dual-profile boundary, exact historical artifact
    recomputation, unchanged reused-seed controls, a pushed preregistration,
    and an explicit later one-shot execution gate.
15. Preserve the consumed r2 successor registration, one-shot execution,
    finalized zero-row `potion_metadata_missing` failure, and all six canonical
    artifacts byte-for-byte. Do not retry r2, repair it in place, prepare r3,
    or reinterpret the result as policy quality or baseline-floor evidence.
16. Treat the three statically proven potion display-name differences as a
    separate offline compatibility defect. Any repair must use a closed mapping
    keyed by stable native potion ID, add regressions for every known pair, and
    fail closed on unknown or inconsistent identities. It grants no execution,
    fresh-evidence, gameplay, OPE, model, reward, training, or promotion
    authority.
17. Preserve the completed potion metadata identity audit and closed three-pair
    repair. It canonicalizes only aliased typed potion names while preserving
    stable native ID, slot, price, source bytes, exact-name behavior, and
    fail-closed handling. It cannot reinterpret either consumed diagnostic or
    authorize r3, a fresh cohort, gameplay, OPE, fitting, reward work, formal
    RL, training, qualification, loading, or promotion.
18. Preserve the completed card/relic metadata identity audit and closed relic
    repair. All 370 audited native card display names match metadata; the relic
    bridge binds exactly 15 aliases and two simulator fallback exemptions to
    stable native IDs. Together with the potion repair, this closes the known
    static item-name hydration gaps without changing policy or evidence
    authority.
19. Preserve the post-repair Current baseline registration, authorization,
    terminal journal, 18 retained rows, canonical artifacts, and
    `study_blocked` verdict byte-for-byte. Do not retry, replace, tune, or treat
    the partial rows as a completed canary or baseline floor.
20. Keep formal non-combat RL `no_go`. Baseline policy and target-supported
    outcome support remain blocked; the latter still has zero supported
    victories and no source-comparable evidence.
21. Preserve the completed card metadata cost-domain audit and closed 20-ID
    repair. It hydrates only exact empty-cost `Unplayable.` metadata shapes as
    SpireComm cost `-2`; all field drift and unlisted empty-cost identities stay
    blocked. It grants no study retry, empirical cohort, gameplay, OPE, fitting,
    reward, formal-RL, training, qualification, loading, or promotion authority.
22. Preserve the bounded simulator-only RL experiment's terminal
    `experiment_blocked` artifacts and consumed logical execution identity.
    The registered native module failed to load before environment construction,
    so seeds `50000..51663`, training, prefix replay, canary, and holdout were
    untouched. Do not retry or repair this execution in place. The Windows
    native-load/preflight gap is closed for future source, with experiment start
    defined by durable output and the started journal rather than repeatable
    compatibility validation. Any successor still requires a separately
    reviewed registration, execution identity, and cohort decision. Every
    successor must preserve `not_ready_for_bounded_training_proposal` and the
    blocked Current-baseline and target-supported-outcome requirements.
23. Preserve the r2 cohort-reuse inventory and all-false preregistration. The
    exact cohort is retained only because r1 exposed no seed-dependent state or
    outcome; the two tracked registration copies are one logical terminal
    predecessor. Do not treat preregistration as execution consent. The next
    possible step is a separate exact authorization binding the pushed r2
    registration, new logical execution identity, output path, unchanged
    `28,800`-second CPU bound, and no-retry contract, followed by source-only
    preflight before native loading or seed access.

## Work Lanes

The offline production candidate-schema fix, anti-retry review, r2 successor,
potion, relic, and card-cost identity repairs, and post-repair Current baseline
study are complete. The study is a terminal blocked result after 18 partial
canary rows; the later repair does not complete it or establish a baseline
floor. Formal RL remains `no_go` because baseline policy and source-comparable
target-supported outcomes are still blocked.

Do not prepare another baseline cohort or modify the consumed study. The card
metadata cost audit and its bounded compatibility repair are closed. The
simulator-only experiment is also closed as a terminal native-load failure,
without training or evaluation evidence. Its read-only Windows loadability
audit and source-only start-boundary repair are complete. The r2 successor is
preregistered with all authority false and reuses only the untouched cohort,
not the consumed r1 logical identity. Its exact execution authorization and
full source-only preflight remain separate future gates. A rebuilt module or
different experiment still requires a separate OpenSpec change. A new
empirical Current-baseline strategy still requires a separate project-level
decision with a fresh identity and evidence design; it is not an automatic
successor to either the consumed study or this simulator-only preregistration.

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
