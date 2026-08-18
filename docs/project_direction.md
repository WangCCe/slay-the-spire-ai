# Project Direction

Last updated: 2026-08-18

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

The state-conditioned simulator-learning successor has now completed its one
authorized logical execution. It trained for 4,096 episodes and 64 optimizer
updates, then completed all 128 paired canary seeds with exact replay. The
trained policy improved effective floor against its frozen initialization by
`+10.75`; the registered 95% bootstrap interval was
`[8.9609375, 12.5390625]`. Both policies still recorded zero victories, and no
training or canary policy episode reached floor 51.

The canary correctly stopped on the sole registered blocker
`card_reward_selected_kind_saturation`: the trained policy selected `take` on
all 1,458 card-reward decisions despite 1,437 skip opportunities. Holdout seeds
`71152..71663` were not accessed. The standalone standard-library verifier
accepted all 75 terminal artifacts, 64 checkpoints, 4,096 training episodes,
and the terminal verdict `experiment_stopped_at_canary`. CommunicationMod and
the complete production-checkpoint inventory remained byte-unchanged.

The state channel did affect relative candidate scores and changed ordering on
366 of 3,556 trained canary multi-candidate decisions, so r2's deterministic
state-cancellation defect is closed. The remaining failure is behavioral, not
architectural sufficiency: a positive floor signal against seeded
initialization cannot override action-family collapse or zero victory evidence.
An immediate successor experiment is therefore `no_go`. The next gate is a
read-only audit of the existing rows and checkpoints to locate the card-reward
collapse mechanism before any algorithm proposal.

That deterministic read-only audit is now complete. It retained `31,571`
training card-reward decisions: `31,306` exposed `skip` and `265` exposed
Singing Bowl as the alternative to taking a card. Stochastic training samples
never produced an all-`take` chunk, but the score-greedy policy first became
strictly all-`take` on chunk `2` and remained so through chunk `63`. Because
chunk `n` is scored before optimizer update `n + 1`, the persistent collapse
was already present after the second optimizer update; later entropy-driven
sampling continued to select some skips without restoring the greedy boundary.

The retained scores separate structural and learned pressure. Across eligible
training decisions, `take` candidates occupied mean candidate share
`0.749936646862156`, while reconstructed mean `take` probability was
`0.808513819581934`, an excess of `0.0585771727197777` beyond multiplicity.
By chunk `63`, mean `take` probability reached `0.877009449037648` and every
best-take/skip margin was positive, with minimum `0.530952155590057`. Mean
candidate entropy was `1.36443426492975`, but mean action-kind entropy was only
`0.482950407917238`; the `0.881483857012509` gap shows that candidate-level
entropy can remain broad within several card choices while providing much less
diversity between `take` and `skip`.

This narrows the mechanism to evidence consistent with candidate-level softmax
multiplicity plus learned take-score amplification and an entropy objective
that does not directly protect action-family diversity. It is not a causal
ablation: reward, optimizer, entropy coefficient, architecture, and any
correction remain unresolved. The JSON and Markdown audit reproduced
byte-identically, and the independent terminal verifier still accepted all 75
source artifacts and 64 checkpoints after publication.

No successor execution is authorized. The next gate is a source-only design
review for an action-family-normalized or hierarchical candidate policy. It
must prove synthetic invariants such as equal family mass under equal logits,
invariance to duplicate same-family candidates, preserved within-family card
ordering, and explicit family-level entropy before any fresh cohort,
registration, or simulator run is proposed.

The later hierarchical successor and its fixed read-only credit-assignment
audit are now complete. The audit exactly reconstructed 11,807 decisions from
512 training episodes and retained all 3,559 multi-family card rewards,
including 17 sampled Singing Bowl choices. Aggregate combined direct take-
logit pressure was positive in every chunk, and the unique greedy `take` margin
grew strictly across terminal chunks 4 through 7. The bounded verdict is
`direct_take_pressure_aligned_but_stratum_heterogeneous`: the supported
effective-floor `17..33` band had nonpositive combined pressure
(`-0.0010187720362788734`) across 171 decisions while every other supported
fixed band was positive.

This is descriptive objective evidence, not a full shared-parameter gradient,
causal card value, or intervention result. It does not justify changing the
reward, either entropy coefficient, the advantage estimator, architecture, or
checkpoint selection. Both fresh source-only publications produced JSON
SHA-256 `5ee6677e26ddc7c6c5fb57b3325a1da805cf1856dc56bca1ac28354aa7e0ba99`
and Markdown SHA-256
`02c76303ed1020403f83cbf789068e8b0eb4bd43581ad4657b3b633581e8fde1`.
The next gate may only be a separately reviewed source-only algorithm-design
proposal. It must address trajectory-confounded advantages and specify how a
future registration would expose shared-parameter attribution before seeking
new model-loading, cohort, training, or experiment authority.

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
23. Preserve the r2 cohort-reuse inventory, registration, authorization,
    source-only preflight, terminal journal, 64 checkpoints and training
    summaries, evaluation, model, report, and manifest byte-for-byte. The
    single logical execution completed 4,096 training episodes and the
    registered replay, canary, and conditional holdout within 13,977.62
    cumulative seconds. Canary passed; trained-minus-initial terminal floor was
    `+10.3515625` with 95% interval `[8.5390625, 12.15625]`. Holdout then
    measured `+10.53125` with interval `[9.685546875, 11.3984375]`, but both
    policies won 0/512 holdout episodes. Preserve the valid terminal verdict
    `experiment_valid_without_learning_signal`; do not rerun, tune, reuse the
    cohort, load the model into Current, or claim formal-RL or promotion
    authority.
24. Preserve the completed r2 read-only terminal postmortem and its bound JSON
    evidence. The floor shift is broad and survives removal of unsupported
    pairs, but all 5,376 training/evaluation policy episodes had zero victories,
    no policy episode reached floor 51, and the final greedy policy selected
    `take` for every observed canary and holdout card reward. More importantly,
    the registered linear scorer adds one shared state vector to every candidate,
    so state-only features cancel exactly from relative logits. An immediate r3
    is `no_go`. The next change must first make candidate ranking state
    conditioned, add anti-collapse diagnostics and regressions, and retain the
    existing baseline/outcome blockers. Any later experiment requires an
    evidence-backed hypothesis, fresh identity, fresh cohort decision, and
    separate OpenSpec approval.
25. Preserve the additive state-conditioned ranker capability and diagnostics.
    The new one-hidden-layer scorer keeps state and candidate tensors separate,
    and a fixed regression proves that changing only state can reverse an
    unchanged candidate ordering. The separate standard-library diagnostics
    report complete candidate-kind opportunities, selections, exact saturation,
    and raw margins without importing Torch. Focused pytest passed 23 tests; the
    registered commit gate passed 3,828 tests with 11 skips; strict OpenSpec
    passed 64 items; and the unchanged r2 verifier still passed all 225,389
    checks. No production path imports either module. This capability grants no
    r3, training, cohort, replay, model-loading, gameplay, formal-RL,
    qualification, or promotion authority.
26. Preserve the completed state-conditioned successor design audit. It selects
    one additive source-only `add-state-conditioned-noncombat-policy-input`
    change: exact API v3 projection into separate state and candidate tensors,
    stable feature identity, and canonical anti-collapse diagnostic rows. It
    must not edit the r2-bound experiment source or start an r3. Current remains
    the only eligible non-teacher primary comparator, but its structural
    closure and credible floor remain unproved; SimpleAgent, Bottled, and seeded
    initialization retain auxiliary-only roles. A distinct Current readiness
    review and baseline proposal must precede any fresh state-conditioned
    experiment, while target-supported outcomes remain independently blocked.
27. Preserve the additive state-conditioned policy-input capability. The new
    source-only module reuses exact API v3 leakage-controlled projection but
    emits one state tensor and a separate candidate matrix, binds stable input
    metadata, and builds canonical scored-decision rows for anti-collapse
    diagnostics. RED failed only on the missing module; the new module then
    passed 21 focused tests, and the combined input/ranker/diagnostic/r2
    projection selection passed 54 tests with 92 deselected. No production,
    script, or existing experiment path imports it, and the unchanged r2
    verifier still passes 202 artifacts and 225,389 checks. The repository
    `commit` gate passed 3,849 tests with 11 skips in 315.24 seconds, 318.47
    seconds including orchestration. Correctness passed, but the five-minute
    feedback bound remains missed by 18.47 seconds. This capability grants no
    experiment, cohort, native loading, training, gameplay, model loading,
    formal-RL, qualification, or promotion authority.
28. Preserve the post-repair Current comparator readiness review. The known
    event, shop, candidate-schema, potion, card, relic, and card-cost bridge
    defects are closed at their source and regression boundaries, the bound
    Current policy and old numeric gates remain unchanged, and the focused
    offline chain passes 278 tests with 5 expected skips. The current main spec
    still over-broadly forbids any successor after the `Injury` measurement
    failure. The next change may revise that boundary and propose exactly one
    distinct post-final-repair Current-versus-first-candidate replication with
    a regenerated untouched cohort. It must preserve the consumed study,
    retain the old thresholds or make them stricter, and make any new
    structural or quality failure terminal for the Current-baseline lane. This
    grants proposal consideration only; no cohort selection, native loading,
    execution, training, gameplay, formal-RL, qualification, or promotion is
    authorized.
29. Preserve the unique final Current baseline replication and its invalid
    terminal publication. All 16 canary pairs completed and passed: Current
    mean floor was `25.0625`, control mean floor was `14.1875`, and the paired
    mean floor difference was `+10.875`. Only five of 64 holdout pairs were
    retained before terminal publication failed with Windows `PermissionError`
    while atomically replacing the execution journal. The retained rows are
    descriptive only; the registered bootstrap, canonical metrics, report,
    manifest, and terminal verdict are absent, so no baseline floor is
    established. The same-question attempt is consumed, Current is no longer
    an eligible baseline candidate, and formal non-combat RL remains `no_go`
    because both baseline policy and target-supported outcome support are
    blocked. Read-only monitoring overlapped the active output-root writes, so
    a Windows sharing conflict is a plausible but unproven contributor. Do not
    retry, resume, repair, replace seeds, or reinterpret this result.
30. Preserve the read-only baseline-strategy options audit. No existing policy
    can replace Current as policy-quality truth: SimpleAgent and Bottled remain
    auxiliary, seeded initialization is only a training control, and learned
    imitation lanes remain negative evidence. The selected next direction is a
    distinct state-conditioned simulator-learning experiment that compares a
    trained policy only with its frozen initialization, requires explicit
    anti-collapse and state-effect gates, and cannot establish policy quality,
    formal-RL readiness, live value, or promotion. The active
    `add-state-conditioned-noncombat-simulator-learning-experiment` change is
    source-only planning until implementation, registration, cohort, limits,
    and exact authorization are separately committed and pushed. Target-
    supported outcomes remain independently blocked.
31. Preserve the state-conditioned successor registration, authorization,
    complete local terminal bundle, deterministic large-row archive, 64
    checkpoints, model, canary evidence, and
    `experiment_stopped_at_canary` verdict. Do not retry, tune, inspect the
    untouched holdout, select an intermediate checkpoint, or load the model
    into gameplay. The paired canary floor signal is real against frozen
    initialization, and state-conditioned relative scoring is demonstrated,
    but all 1,458 trained card-reward decisions selected `take` and every
    training/canary episode had zero victory. Formal RL, policy quality,
    target-supported outcomes, qualification, loading, and promotion remain
    `no_go`. The next change may perform only a read-only existing-artifact
    collapse audit before considering a new algorithm proposal.
32. Preserve the completed state-conditioned card-reward collapse audit and its
    exact source allowlist, trajectory reconstruction, and deterministic report.
    It locates persistent greedy `take` saturation at training chunk `2`,
    measures both candidate-count pressure and learned score amplification, and
    shows that candidate entropy overstates family diversity. These are bounded
    observations, not reward, optimizer, architecture, or intervention
    causality, and they grant no replay, training, holdout, or successor-run
    authority.
33. Preserve the additive source-only action-family distribution capability.
    It groups validated candidates by `kind`, uses the best candidate score as
    each family logit, and factorizes probability into family and conditional
    softmaxes with explicit family, conditional, and joint entropy. Ranker
    scores enter as CPU float32 and distribution tensors remain finite CPU
    float64, including opposite float32 limits; exact hierarchical log-
    probability sums and autograd gradients are regression-covered. The
    focused suite passes 24 tests, the repository commit gate passes 4,036 tests
    with 11 skips, and an independent review has no remaining correctness
    finding. The module is not imported by any runner, defines no greedy rule or
    entropy coefficient, and keeps all experiment, seed, native, training,
    gameplay, loading, formal-RL, qualification, and promotion authority false.
34. Preserve the strict read-only action-family counterfactual audit over the
    exact collapse-audit-bound scored rows. Across 107,104 training decisions,
    joint-probability argmax differs from raw-score argmax for 27,106 of 31,571
    card rewards (`85.86%`) and 5,724 of 9,180 shops (`62.35%`). The trained
    canary still changes 353 of 1,458 card rewards (`24.21%`) and 380 of 663
    shops (`57.32%`). Most changes move the score-best `take` or `buy_card`
    family to singleton `skip`, `leave`, or `remove_card` candidates after
    within-family probability splitting. Event and route rows remain exact
    one-family fallbacks with zero family entropy and no argmax changes. All
    115,908 rows have no score ties, no two-stage score-argmax mismatch, and no
    probability or entropy invariant violation. Therefore joint-probability
    argmax is not a neutral greedy rule, and family entropy alone is incomplete
    for event and route. The combined focused boundary passes 43 tests with 5
    symlink-permission skips, the repository commit gate passes 4,055 tests with
    16 skips, and a three-round independent review has no remaining P1, P2, or
    P3 finding. This audit grants no deterministic-selection, entropy-
    coefficient, training-objective, experiment, loading, formal-RL, gameplay,
    qualification, or promotion authority.
35. Preserve the additive source-only hierarchical policy-objective contract.
    It resolves one selected action by stable `action_id`, exposes exact family,
    conditional, and joint log-probability tensors, and keeps family, expected
    conditional, and joint entropy separately differentiable. Deterministic
    metadata returns the complete raw-score maximum set with no tie-breaking;
    an independently reconstructed two-stage max-score set must match it, and
    joint-probability argmax is not an API. Event and route retain exact one-
    family fallback while conditional objective and entropy terms remain live.
    All terms stay finite CPU float64 over CPU float32 scores, including opposite
    float32 limits. The focused suite passes 20 tests, the dependency-focused
    boundary passes 44, the repository commit gate passes 4,075 tests with 16
    skips, and independent review has no remaining P1 or P2. The capability
    accepts no coefficient, reward, return, advantage, sampling, or loss and is
    absent from experiment, verifier, agent, and `main` imports. It grants no
    execution, training, loading, native, seed, formal-RL, gameplay,
    qualification, or promotion authority.
36. Preserve the source-only hierarchical simulator-learning successor
    proposal. It selects a new additive three-module identity without modifying
    or privately importing the consumed experiment, uses candidate `kind` for
    family-first then conditional sampling, fixes independently bound family
    and expected-conditional entropy coefficients at `0.01`, and retains the
    prior ranker, formal reward, optimizer, gradient, and raw-score evaluation
    controls. Raw-score ties fail closed. A four-chunk exact family-saturation
    stop protects canary, while card-reward and shop canary gates protect a
    newly inventoried holdout. Fresh cohort counts are fixed at `1024/128/512`;
    ceilings are `4,096` training, `2,560` evaluation/replay, `6,656` total
    episodes and `28,800` CPU seconds. A durable write-ahead marker separates
    repeatable pre-seed setup from the evidence-bearing identity. The proposal
    and global OpenSpec set pass strict validation (`72/72`), but this planning
    boundary grants no implementation, registration, cohort, native, seed,
    training, loading, gameplay, formal-RL, qualification, or promotion
    authority.
37. Preserve the completed hierarchical simulator-learning registration,
    authorization, full terminal bundle, and
    `experiment_stopped_during_training_for_family_saturation` verdict. The
    process exited cleanly after 512 training episodes, 8 optimizer updates,
    8 checkpoints, 11,807 decisions, and 2,165.452 charged seconds, with zero
    canary or holdout access. All 1,847 multi-family card-reward decisions in
    the final four chunks had `take` as the unique raw-score maximum family,
    even though family entropy remained close to `ln(2)` and sampled `take`
    versus `skip` stayed near balanced. Mean take score margin grew from
    `0.0165` in chunk 0 to `0.0959` in chunk 7. Training reached mean floor
    `12.629`, max floor `44`, and zero victories. A verifier-only float32
    reduction repair left all artifacts unchanged; 92 focused tests passed and
    strict repository verification accepted 22 artifacts, 8 checkpoints, and
    8 chunks. Formal RL, policy quality, target-supported outcomes, model
    loading, gameplay, qualification, and promotion remain `no_go`. The next
    work may only audit existing card-reward family credit assignment and
    trajectory confounding before any new algorithm proposal or empirical run.
38. Preserve the completed hierarchical card-reward credit-assignment audit,
    exact input/source bindings, 11,807 aligned decisions, 3,559 eligible card
    rewards, byte-identical JSON/Markdown, and
    `direct_take_pressure_aligned_but_stratum_heterogeneous` verdict. Every
    chunk had positive aggregate direct take-logit pressure and terminal mean
    margins grew strictly, but the supported effective-floor `17..33` band had
    combined pressure `-0.0010187720362788734`. Do not reinterpret direct
    coordinate pressure as a full model gradient or causal effect, and do not
    tune a coefficient, reward, advantage, architecture, checkpoint, or cohort
    from this result. A next change may propose source-only algorithm design
    with synthetic contracts and explicit future shared-parameter attribution;
    it grants no model loading, execution, training, gameplay, formal-RL,
    qualification, or promotion authority.
39. Preserve the additive source-only hierarchical advantage-attribution
    contract and its deterministic JSON/Markdown design evidence. It validates
    trajectory-disjoint baseline and scale provenance, exact residual-over-
    scale arithmetic, five ordered loss components over one shared CPU
    float32 parameter set, an independently differentiated full gradient, and
    one aggregate-first global-norm clip factor at ceiling `1.0`. The fixed
    shared-ranker fixtures preserve aligned and opposing row-local versus
    shared-parameter directions plus within/across-family max-pool ties. The
    focused suite passes 46 tests and the post-review contract,
    hierarchical-objective, and action-family-distribution boundary passes 90.
    Independent review found and closed incomplete non-held-out fit coverage
    and aliased parameter identity. The repository `commit` gate passes 4,241
    tests with 16 skips in 424.62 seconds, 427.54 seconds including
    orchestration.
    This contract fits no baseline and accepts no path, seed, cohort,
    checkpoint, environment, optimizer state, or parameter delta. The next
    gate is a separately reviewed OpenSpec proposal that selects a baseline
    estimator and folds, bounds raw evidence retention, and registers any
    empirical successor lifecycle. It grants no model loading, execution,
    training, gameplay, formal-RL, qualification, or promotion authority.
40. Preserve the source-only cross-fitted hierarchical learning successor and
    its fail-closed execution boundary. The implementation fixes eight chunks
    of 64 trajectories, four trajectory-disjoint folds, a 128-dimensional
    folded sparse baseline, exact five-component shared-gradient accounting,
    independent Adam replay, deterministic binary/gzip evidence, append-only
    access and resource journals, recoverable checkpoints, one bounded
    same-identity infrastructure resume, exact terminal checkpoint closure,
    and an independent standard-library verifier. Review-sensitive control
    and verifier tests pass 130 tests with one skip; the repository `commit`
    gate passes 4,419 tests with 17 skips in 556.07 seconds, 558.90 seconds
    including orchestration. Independent review closed post-isolation terminal
    publication and extra-access saturation-boundary defects. Registration
    rehearsal then exposed and closed a pushed-boundary defect: execution now
    accepts the registered implementation as an ancestor of the later pushed
    registration/authorization HEAD only when the current tree contains both
    exact canonical blobs and all registered source bytes remain unchanged.
    This narrow post-gate repair is covered by RED registration-lineage tests
    and the control/verifier suite. Registration verification also aligned the
    independent inventory replay with the producer's explicit `(seed, source,
    document, JSON path, role)` canonical row order. The one-shot repository
    gate was not rerun for either registration-boundary repair. Deletion of the
    entire immutable output root remains prohibited evidence destruction and
    is outside the local-filesystem trust model; deletion-resistant redemption
    would require a separate external authority proposal. No native module,
    simulator environment, empirical seed, fitting, update, game, or
    CommunicationMod process was loaded or run at the source or registration
    boundary. The final all-false registration binds implementation commit
    `5c8b66cdaf62f51a654994ec5a5cd5c2f6ac1118`, registration SHA-256
    `1a3b267c16524e1e0449a8bddbd482684fb9dd0ac89c20bd9db19a9bd755249c`,
    334 historical sources, 275,853 provenance rows, 5,755 excluded seeds,
    and 512 ascending scheduled seeds `1769..2348`. A fresh independent
    process rebuilt the inventory and accepted every registered source,
    runtime, native, isolation, authority, and absent-output identity. Focused
    registration tests pass 20 tests and strict OpenSpec validation passes all
    75 items. The independently reconstructed exact execution request has
    SHA-256
    `8f6476b0f4a3fe06969558b8a07ea2c825244223a7d1cc4dd5116364f60a77c3`.
    It requests CPU-only native loading, 512 scheduled seeds `1769..2348`,
    four-fold cross-fitted fitting, at most eight optimizer updates, 576 total
    environment accesses including one same-identity replay reserve, 32,768
    retained decisions, and 14,400 charged seconds. Evaluation, formal RL,
    gameplay, CommunicationMod, production model loading, qualification, and
    promotion remain false. The operator separately approved this exact digest
    on 2026-08-07. The canonical approval has SHA-256
    `3c16ab2541a1daaf0377539e47f4fb49ec6c72025d64b78528ffaf7e163b9945`
    and its independently reconstructed authorization has SHA-256
    `c711b13d1728187ce0c0bb09136c9f86658bbf7de86470707c65b58e5c57c473`.
    The single authorized logical execution is now consumed and independently
    valid as `experiment_failed_after_seed_access`. It durably debited seeds
    `1769..1780`: 11 accesses completed and the twelfth failed its registered
    wall-time check before environment construction. No chunk, baseline,
    retained decision bundle, optimizer update, checkpoint, gradient evidence,
    or evaluation was published. The verifier accepted all 13 managed
    artifacts, exact approval/authorization identity, access/resource prefixes,
    unchanged pre/post isolation, and terminal SHA-256
    `1887395ae2e4e23d031a3370695e6f694b6ba079ba8b110ceb36b34642e452d8`.
    No resume or retry is permitted. A read-only terminal postmortem records one
    monitoring deviation: the outer wrapper timed out while the Python child
    still held the lease, causing a read-only active-root inspection before
    child liveness was discovered; no artifact changed and final verification
    ran only after natural child exit. The separate execution-bottleneck audit
    finds that parsing the 63,171,200-byte registration takes `0.530` seconds
    but one `_registration_for_identity` takes `56.016` seconds. One completed
    access enters that helper at least 20 times, before additional registration
    hashing, so repeated whole-registration validation dominates the run. It
    also finds that non-infrastructure pre-checkpoint failure leaves the
    verified ledger at `charged_seconds=0.0` and that producer terminalization
    took about 2,228 seconds from failure witness to manifest. Focused terminal
    tests pass 130 tests with one skip, and strict OpenSpec validation passes all
    75 items. The source-only control-plane repair is recorded separately in
    item 41. The consumed execution remains non-retryable and grants no new
    experiment, native, seed, training, model-loading, gameplay, formal-RL,
    qualification, or promotion authority.
41. Preserve the source-only cross-fitted execution control-plane repair and
    its deterministic JSON/Markdown closeout. One private context now validates
    and owns the complete registration once, exposes recursively immutable
    JSON-compatible values, and reuses its bound digest, identity, and output
    through journal, resource, checkpoint, failure, isolation, and terminal
    operations. Every post-start terminal path closes with an exact bounded
    `terminal-attempt-charge`; same-process publication carries its canonical
    intent forward while interrupted recovery still reopens raw durable bytes.
    The independent verifier holds a dead-owner lease across its full evidence
    read, binds the locked descriptor to the checked path, and admits a
    lease-free archived root only after regular terminal and manifest markers
    plus a final pre-enumeration lease check. Read-only independent review found
    and closed mutable context values, a lease-free boundary race, and lease
    path/handle replacement. Focused review regressions pass 3 tests and the
    final source-only suite passes 193 tests with one skip. The repository
    `commit` gate passes 4,434 tests with 17 skips in 657.01 seconds, 659.89
    seconds including orchestration. No native module, registered seed,
    environment, fitting, training, evaluation, OPE, gameplay,
    CommunicationMod, qualification, or promotion was run. Any empirical
    successor requires a separately reviewed proposal, new pushed source
    identity, fresh registration and cohort decision, exact request, and
    separate explicit human approval. The five additive requirements are
    synced to the main successor spec and the completed change is archived at
    `openspec/changes/archive/2026-08-07-repair-cross-fitted-execution-control-plane`.
42. Preserve the terminal `no_go_source_binding` result from the one-shot
    cross-fitted empirical-successor readiness audit. Source commit
    `863ae5a4046df110e4f9028bb3c56d556a7c6a43` was pushed and consumed exactly
    once by audit
    `noncombat-cross-fitted-empirical-successor-readiness-20260808-r1`. The
    source gate stopped before candidate inventory reconstruction, rehearsal,
    native loading, environment construction, seed access, fitting, training,
    evaluation, OPE, gameplay, CommunicationMod, qualification, or promotion.
    No canonical output directory was installed and no empirical-successor
    registration proposal became eligible. Independent receipt review confirms
    canonical started and terminal JSON, matching attempt identity, valid
    SHA-256 values
    `132cfaea05dc7e23b0140fa6b63dc253e60256bea0b8fc6dc5accb3c281a9e71`
    and
    `e3bffa6c509ba00a7c28b607cfdcebecfe3021cf004f61b87b14cc8f47870d71`,
    all-false authority, and absent output, scratch, and staging paths. The
    bound registration correctly has eight schedule fields; the readiness
    implementation incorrectly allowed only five and rejected the provenance
    fields `canonical_search_start`, `inventory_sha256`, and
    `selection_schema_version`. The identity is non-retryable. The next step is
    a new source-only OpenSpec correction with the exact bound schedule schema
    and regression coverage, followed by a new pushed source identity; it is
    not permission to rerun, register, or execute an empirical successor. The
    completed readiness change is synced to the main spec and archived at
    `openspec/changes/archive/2026-08-07-assess-cross-fitted-empirical-successor-readiness`.
43. Preserve the completed source-only readiness binding correction at commit
    `54b266b4ba1b4993faded5fc366532598d81b9f6`. The auditor and independent
    verifier now require the exact eight-field consumed schedule, pin canonical
    search start `0`, inventory SHA-256
    `435cf41b1cff21178d6de253677544b0e96f8b8ec431c181981aef36591a7174`,
    and selection schema
    `noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1`, and bind
    the synced canonical main readiness spec. The auditor also rejects any
    source-binding input inventory that differs from its exact declared role
    and path sequence before Git blob I/O. Focused source-only verification
    passed 81 tests with one explicit actual-scale skip, both specs passed
    strict validation, and independent review closed without findings. No
    readiness auditor, native module, runtime, model, empirical seed outcome,
    training, evaluation, game, or CommunicationMod operation was run. The
    main spec is synced and the completed change is archived at
    `openspec/changes/archive/2026-08-07-repair-cross-fitted-readiness-source-binding`.
    This correction does not revive source commit `863ae5a4046df110e4f9028bb3c56d556a7c6a43`
    or authorize another readiness attempt. A later source-only OpenSpec change
    must separately establish fresh-identity eligibility, exact attempt paths
    and identity, and one-shot authorization before the auditor is invoked.
44. Preserve the independently verified `go` from the corrected-source
    readiness audit. Pushed source commit
    `522185d06ddf48cb1be095c16efacaad299a0197` was claimed exactly once by audit
    `noncombat-cross-fitted-empirical-successor-readiness-20260808-r2`; the
    source-only command exited successfully after 959.3 seconds. All six fixed
    gates passed. The rebuilt candidate has 512 seeds, zero collisions with all
    512 consumed positions, candidate schedule SHA-256
    `121d1f847ed02c437c8f6dfd60494e378df3d43b36f1cfb2384de94f20e12c56`,
    and fixed projected margin 4,303.644 seconds. The independently verified
    publication is
    `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r2`;
    its candidate artifact SHA-256 is
    `7b5b2d9da9fe0b0cdb2dc9a298b395783171dbf9ecf46b941af92ba809e3695d`
    and readiness identity is
    `4f3da3b53426f1bb811fbdb3eaccb670bf03e52c221e67df6b1be6f65038897b`.
    A second standalone verifier independently rebuilt and checked the complete
    publication in 414.4 seconds. Canonical attempt SHA-256
    `9062a3bd258c1e95adc4c9954fcd1a6b1085c2a6e6f1dd665a5f65d7214e648c`
    and verification-receipt SHA-256
    `d37549b6cc8d026f1feaf7373a26a2bdabb6175da733f6b786a5c6827355ee59`
    link the source and installed files; scratch, staging, sealed, claim, and
    child-process remnants are absent. All 18 authority and all 10 empirical-
    operation fields are false. This `go` makes only a separate empirical-
    successor registration proposal eligible. It does not register a cohort,
    authorize native or model loading, access an empirical seed outcome, fit,
    train, evaluate, run OPE, launch gameplay or CommunicationMod, qualify, or
    promote. The deterministic closeout is
    `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r2_closeout.json`.
    The already-synced execution change is archived at
    `openspec/changes/archive/2026-08-08-run-cross-fitted-readiness-20260808-r2`.
45. Preserve the completed source-only compact-registration transport change.
    New successor registrations use schema
    `noncombat-cross-fitted-hierarchical-learning-registration-v2`, retain the
    complete 8x64 schedule, and bind the immutable readiness publication,
    verification receipt, report, deterministic-gzip candidate, and consumed
    registration source without embedding the 347,575,355-byte canonical
    inventory. Historical v1 evidence remains independently verifiable against
    its registered Git source, while the public v1 builder now fails closed.
    Independent review found and closed four defects: schema-global public
    symbols that broke historical v1 validation, metadata-only consumed-cohort
    binding, a still-callable new-v1 builder, and Python numeric equality that
    admitted non-boolean authority or non-integer counts. Full source-only
    verification passes 71 control-plane tests, 22 seed-inventory tests, one
    preservation test, 81 readiness tests with one skip, and 118 independent-
    verifier tests with one skip. No registration, request, approval,
    authorization, native or model load, seed access, fitting, training,
    evaluation, OPE, gameplay, CommunicationMod, qualification, or promotion
    was created or run. The r2 `go` remains immutable historical evidence for
    source commit `522185d06ddf48cb1be095c16efacaad299a0197`, but it is obsolete
    for any registration whose source includes this control-plane change and
    grants no proposal eligibility to that new source. A separately
    preregistered one-shot r3 readiness audit must bind the new pushed source
    and complete independently before any compact registration is proposed.
46. Preserve the consumed r3 readiness failure without repairing or retrying
    it. Pushed source commit
    `5777eef4a43065e6246481926f95d6cfcba04c88` was invoked exactly once by audit
    `noncombat-cross-fitted-empirical-successor-readiness-20260808-r3` and
    exited with code 1 after 760.7 seconds. Source, cohort, rehearsal,
    control-plane, and budget work completed before artifact publication stopped
    as `no_go_artifact_binding`: the candidate canonical JSON crossed the fixed
    512 MiB ceiling. No canonical output, scratch, or sealed sibling remains.
    The canonical started and terminal receipts have valid identity linkage,
    digests, and all-false authority and empirical-operation maps, but the exact
    staging directory remains with one incomplete 6,763,664-byte gzip. The
    preregistered independent terminal review therefore fails solely on
    `staging_absent=false`; the terminal receipts are not claimed as
    independently verified, and no compact registration proposal is eligible.
    Preserve the receipts and staging as immutable failure evidence. Do not
    delete, repair, resume, or retry this source identity. Source review confirms
    two separate defects for a later source-only correction: seed inventory
    scans all tracked `reports/*.json.gz` inputs and recursively ingests the r2
    candidate's 1,676,494 historical rows, while the readiness exception path
    terminalizes without removing an already-created staging directory. A later
    attempt requires a new OpenSpec correction, pushed source identity, exact
    paths, and separate authorization. This run loaded no native, runtime,
    model, game, or CommunicationMod code and performed no empirical seed
    access, fitting, training, evaluation, or OPE. The deterministic closeout is
    `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r3_closeout.json`.
47. Preserve the completed source-only readiness artifact-boundary repair. The
    seed helper, actual streamed producer, and standalone verifier now exclude
    both exact readiness-derived report namespaces before format selection,
    Git blob loading, decompression, parsing, or recursive seed extraction, so
    prior candidates, receipts, closeouts, staging, and sealed siblings cannot
    recursively inflate a later candidate. Legitimate and lookalike report
    paths retain their prior handling, and producer/verifier source bindings
    remain independently reproducible. The runner now records exact staging
    ownership, rejects lexical pre-existing paths, retires owned staging through
    an atomic random quarantine with post-rename identity verification, restores
    replaced or cleanup-failed paths, and uses the same ownership boundary for
    successful sealing. Terminal receipts are written only after owned staging
    is absent or cleanup has failed closed as `no_go_artifact_binding`. Focused
    source-only verification passes 119 tests with one explicit skip; strict
    OpenSpec validation passes all 77 items; Python compilation and final
    independent review complete without findings. The repository commit gate
    was invoked exactly once but is inconclusive: the outer command returned
    exit 124 after 904.4 seconds without a pytest summary, and its surviving
    exact runner/pytest processes were terminated by PID and confirmed absent.
    The gate was not retried. No readiness r4, native or model load, empirical
    seed access, fitting, training, evaluation, OPE, gameplay, CommunicationMod,
    qualification, or promotion was run or authorized. The main spec is synced
    and the completed change is archived at
    `openspec/changes/archive/2026-08-08-repair-cross-fitted-readiness-artifact-boundary`.
    This correction does not repair, verify, revive, or authorize retry of r3.
    Any later attempt requires a new pushed source, proposal, exact identity and
    paths, preregistration, and explicit one-shot authorization.
48. Preserve the independently verified repaired-source r4 readiness `go`.
    Pushed source commit `0570aa23adc46df0801d18769b0bbc8adbe53c55`
    was invoked exactly once by audit
    `noncombat-cross-fitted-empirical-successor-readiness-20260808-r4` and
    exited 0 after 1021.8 seconds. All six fixed gates passed. The candidate
    contains 512 fresh seeds, excludes the consumed 512-seed cohort with zero
    collisions, and retains `4303.644` seconds of fixed-budget margin. The
    canonical three-file publication is installed at
    `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r4`;
    scratch, exact staging, and sealed siblings are absent. A separate
    standalone verifier completed in 448.1 seconds with status `verified`,
    readiness identity
    `6723364a5a31c177bad0a4e8980bfbc6ff74914d595a506d434387c9bbcc3b8f`,
    and no findings. Native loading, seed access, model loading, fitting,
    training, evaluation, OPE, gameplay, CommunicationMod, qualification, and
    promotion all remained false. This `go` makes only a new empirical-
    successor registration proposal eligible; it does not register a cohort or
    authorize execution or training. Preserve the publication, source-keyed
    receipts, and deterministic closeout at
    `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r4_closeout.json`.
    Before any later irreversible execution, replace the long copy-pasted
    authorization tuple with a tracked machine-generated manifest and the solo
    maintainer's standing delegation, while retaining exact source/path/limit
    validation, atomic claim, durable receipts, and no-retry semantics.
49. Preserve the source-only solo-maintainer execution-delegation control
    plane. Standing-delegation v1 retains the exact external-human grant,
    timestamp and message/task provenance, binds `origin/master`, the successor
    registration-id prefix, the actual execution-request schema version, a
    closed exclusion set, the external publication-time revocation rule, and a
    canonical body digest. Delegated-approval v2 embeds that complete grant and
    a machine resolution to one exact request digest; authorization v1 embeds
    the normalized approval unchanged, while historical external-human
    approval v1 and consumed evidence remain byte-preserved. Source-only CLI
    commands inspect the grant and render approval/authorization candidates to
    stdout without publication or empirical authority. Focused producer,
    lifecycle, verifier, preservation, and import-isolation verification passed
    206 tests with one skip; strict OpenSpec validation passed all 77 items.
    Independent review found and fixed a request-class alias that was not the
    actual request schema and expanded invalid CLI coverage. The repository
    commit gate was invoked once and completed after 1244.73 seconds with 4603
    passed, 18 skipped, and one failed suite-order assertion because Torch had
    already been imported by prior tests. The assertion now compares the module
    set before and after source-only rendering; the exact failed node and two
    fresh import-isolation nodes pass three tests in 2.02 seconds. The commit
    gate is not rerun. No native/model load, environment, seed, fitting,
    training, evaluation, OPE, gameplay, CommunicationMod, qualification,
    promotion, or empirical output occurred. Because delegation changes source
    and canonical contract bytes, r4 remains immutable historical evidence but
    is no longer registration eligibility for this source. The next step is a
    separate preregistered, independently verified fresh source-only readiness
    change; no successor registration or execution may precede its `go`.
50. Preserve the independently verified delegated-source r5 readiness `go`.
    Pushed source `ffd9acc444258483d172529eccfe8ccb05c9bb9b` was invoked
    exactly once by audit
    `noncombat-cross-fitted-empirical-successor-readiness-20260808-r5` under
    the recorded solo-maintainer standing delegation and exited 0 after 994.8
    seconds. All six fixed gates passed. The candidate contains 512 seeds with
    zero collision against the 512 consumed seeds and retains `4303.644`
    seconds of fixed-budget margin. The canonical three-file publication is at
    `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r5`;
    scratch, source-keyed staging, and sealed siblings are absent. The
    standalone standard-library verifier completed in 457.9 seconds with
    status `verified`, decision `go`, proposal eligibility true, and readiness
    identity
    `cdff8937e6c15b27df582bf8d9d606c2185d94cdcfbe4e4f907d6a0244e48d38`.
    Auditor, verifier, and source-specific descendant processes are absent.
    Native loading, environment or seed access, model loading, fitting,
    training, evaluation, OPE, gameplay, CommunicationMod, qualification, and
    promotion all remained false. This `go` permits only a new empirical-
    successor registration proposal; it does not register a cohort, authorize
    execution, or authorize training. Preserve the publication, source-keyed
    receipts, and deterministic closeout at
    `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r5_closeout.json`.
51. Preserve the pushed compact all-false 20260808-r2 successor registration.
    The preregistered plan commit is
    `cf415afb5782c3553080299615c22a033ac23509`; registration evidence commit
    `7b3221c7b099eda2853bfc405c4a67f5b5a8123a` is exact on
    `origin/master`. The 17,595-byte canonical registration at
    `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_registration.json`
    has SHA-256
    `9d792cadbece4ea21768386904633ebded2e94525fb186bdcbf4a4d7729dbdf9`.
    It binds readiness source `ffd9acc444258483d172529eccfe8ccb05c9bb9b`,
    publication `0c62aff2fb301dd491017bbf2e775c36a177bf67`, readiness
    identity `cdff8937e6c15b27df582bf8d9d606c2185d94cdcfbe4e4f907d6a0244e48d38`,
    source inventory
    `5b7fdacecb1e557fd53188f01b80cb79ea41b262b618d81c191c1094854aea03`,
    the complete 8x64 fresh schedule, seed SHA-256
    `121d1f847ed02c437c8f6dfd60494e378df3d43b36f1cfb2384de94f20e12c56`,
    zero collision, native module
    `7ac2c750fba6e38d4a023cab72a4d67f158fe7f88414058e5876cef5003fcb88`,
    CPU runtime, exact CommunicationMod configuration, and the complete
    208-file production-checkpoint snapshot. The corrected deterministic review
    at
    `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_registration_review.json`
    has self-digest
    `d7bd532afb4b1865735866c93f3b3160f041a5c365956373666008a71d0a8f30`
    and exact full-path candidate binding. Producer and independent standard-
    library validation passed; both JSON files are canonical; blocked dependency
    import delta is empty; the registered output root and every request,
    delegation, approval, authorization, journal, checkpoint, terminal, game,
    and empirical artifact remain absent. One prepublication orchestration check
    stopped before staging because it incorrectly tried to reconstruct historical
    dirty-worktree adapter provenance from clean Git blobs; the published pass
    instead uses the contractually bound tracked provenance and exact current
    module bytes. This created no consumed attempt or partial publication.
    Focused verification passed 11 tests in 25.93 seconds after one sandbox-only
    pytest temp infrastructure failure; canonical/self-digest probes and strict
    OpenSpec validation passed 77/77. No implementation or test source changed,
    so the known long commit gate and fresh gameplay validation were not
    applicable and were not run. This registration grants only eligibility for
    a later separate exact execution-request proposal. It grants no approval,
    authorization, native or model loading, environment construction, seed
    access, fitting, training, evaluation, OPE, gameplay, CommunicationMod,
    qualification, promotion, policy-quality, causal, or formal-RL authority.
52. Preserve the pushed exact non-authorizing 20260808-r2 execution request.
    Initial request plan commit
    `26baf220bf8392994fddab0804fad9a2561941b6` and isolated-bootstrap
    clarification `351b9ced669f443eae155e59ef762a367a00f629`
    precede evidence commit
    `35d317a7a6e5f31d3e2664fb2f7713bcf8f9ab15`, which is exact on
    `origin/master`. The canonical 8,945-byte request at
    `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_execution_request.json`
    has file SHA-256
    `31e3b2844df5f4ee389a58aee08fe537c159fe498320cb219e3681745e0cdf38`
    and canonical request digest
    `6257a36c6573c8c412bb8727736e81b063dd0c7076f1ea5b41a70d4a08206c2e`.
    It binds registration
    `9d792cadbece4ea21768386904633ebded2e94525fb186bdcbf4a4d7729dbdf9`,
    source inventory
    `5b7fdacecb1e557fd53188f01b80cb79ea41b262b618d81c191c1094854aea03`,
    the complete 8x64 schedule, exact native/runtime/output/resource/resume
    terms, and the registered 14,400-second, 576-access, eight-update ceilings.
    Base authority remains all false. Requested authority is true only for
    environment construction, execution, model fitting, native loading, seed
    access, and training; this describes a later authorization candidate and
    grants none of those operations. The deterministic 3,817-byte review at
    `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_execution_request_review.json`
    has file SHA-256
    `95b8f43d02a0e79dbb925c192086cf26c17e59cbf47ead26e7641458c4be0acc`
    and self-digest
    `1badc01d53123abc8efd0279bc622b241d08c704d679e517f8321f7e61b71f96`.
    Producer readiness replay completed in 168.3 seconds; independent
    registration/request validation completed in 89.4 seconds. The first direct-
    file `python -I script.py` invocation failed before output because isolated
    mode removed the repo-local package root and left only a zero-byte staging
    file, which was exactly removed. The pushed plan then records the isolated
    `-I -c` repo-root bootstrap that dispatches the same tracked module `main()`;
    no implementation source or request term changed. Canonical/self-digest and
    authority probes passed, focused verification passed nine tests in 11.17
    seconds, strict OpenSpec passed 77/77, and bounded independent artifact
    review found no blocker. No implementation or test source changed, so the
    long commit gate and gameplay validation were not applicable and were not
    run. The registered output root, standing-delegation resolution, delegated
    approval, authorization, native/model load, environment, seed, fit, train,
    evaluation, execution, game, CommunicationMod, qualification, promotion,
    and terminal artifacts remain absent. This request is eligible only for a
    later separate exact delegated-approval and authorization proposal.
53. Preserve the pushed 20260808-r2 standing delegation, delegated approval,
    and tracked authorization as separate control-plane stages later consumed
    exactly once by item 54. The
    plan commit is `371e612a2a786be42538a058f4adc9a6216dc840`, delegated-
    approval evidence commit is
    `40c36f1a8a0cedbf2325b759687a475890c0d879`, and authorization commit is
    `be76cdf9bc803db264949d47d9ee2e07d2e86834`; all are exact on
    `origin/master`. The reusable 1,114-byte standing-delegation manifest at
    `reports/noncombat_cross_fitted_hierarchical_learning_standing_delegation_20260808.json`
    has file SHA-256
    `6dac765272edc2a730f9d03075c97ebccc373a704fcc6d1bf4674dbc29a699dc`
    and delegation identity
    `9720eede9ca1eb41d65277ec9e1fcff024931c06720d2d322bc4f29c55ae97ff`.
    It preserves the verbatim solo-maintainer grant from external-human message
    `item-22027`, task `019eb771-30f7-7ed2-9af2-ea4b22fadc11`, at
    `2026-08-08T09:46:47Z`, together with closed scope, exclusions, future-
    revocation rule, and self-digest. The final prepublication task-metadata
    check at `2026-08-08T15:43:28Z` found no later explicit revocation; the
    latest user message was `item-22065` (`好 继续`). The 1,708-byte delegated
    approval has file SHA-256
    `2b1df39c3364e0dfd3f5d1252cf1be50a9d87d55736695082769b56eb28711f4`
    and approval identity
    `3786717abcbc82ab4c70a39ae8151feee09cc19f7f44f1cfa5a14257ac25901e`;
    its 2,846-byte review has file SHA-256
    `dab1df6ba1c5a15203b50ab2fcfa4010f2abd36c13391d5481b7fb165d7857cb`
    and self-digest
    `3628ca851430e67ba6cf3db1c6ca7a4fe99371be947c1871ec97b4a4bca9c901`.
    Only after that approval was pushed, the 2,650-byte authorization was
    derived with file SHA-256
    `fa5a032b104db51fc784f65ff1bf5888441714a5203ac293d42a695f2af68a67`
    and authorization identity
    `80dffa2fa2c1d1a9d68d638276c73730415842f085c7d881609a37114d88152f`;
    its 2,688-byte review has file SHA-256
    `1f4f10969a88f145439ae6390591dfd2415ce97afbc48634e86377ca059ed9e1`
    and self-digest
    `70e797f3828ac0ab39b550403b871b21e426b6f540e36b20a86a42099d474962`.
    Producer readiness replay took 172.8 seconds for approval and 169.7 seconds
    for authorization; independent verification took 89.3 and 90.6 seconds.
    Focused control/verifier tests passed 19 tests in 10.59 seconds and again in
    9.97 seconds. Canonical/self-digest probes and strict OpenSpec validation
    passed. One plan-only local model review timed out after 184.4 seconds and
    returned no result; it is not counted as review evidence. Deterministic
    contract audit plus the separate standard-library verifier found no
    publication blocker. No implementation or test source changed, so the
    known long commit gate and fresh gameplay validation were not applicable.
    At this authorization closeout the registered output root remained absent
    and no native/model load,
    environment construction, seed access, fit, training, evaluation,
    execution, gameplay, CommunicationMod, qualification, or promotion has
    had occurred. The pushed authorization permitted only the later separate
    exact execution change recorded by item 54; authorization alone was not
    evidence that execution had started or that the policy was valuable.
54. Preserve the completed 20260808-r2 cross-fitted hierarchical execution and
    its independently verified terminal bundle. Plan commit `d68bfce72e6779fece3f431e8e96d8eaa4150478`
    and preflight commit `afc947e56ce3538c173a0d932773bec44f3ab8cf`
    were pushed before the registered output root was created. The exact
    authorization identity
    `80dffa2fa2c1d1a9d68d638276c73730415842f085c7d881609a37114d88152f`
    was consumed once. The execution completed all eight 64-episode chunks,
    512 environment accesses, eight optimizer updates, eight checkpoints, and
    11,729 retained decisions in 12,101.125 charged seconds without resume or
    failure. The independent standard-library verifier passed in 419 seconds
    with verdict `experiment_completed_with_cross_fitted_mechanism_evidence`,
    terminal SHA-256
    `3de29ce568b0d418f4e1052c4b7c92040d2de316e035b455c47384daf48db1e0`,
    and manifest SHA-256
    `b563fe8f95fa705ffcf7eafe14c40672599e46ad2a611db6f473a654ec8860eb`.
    Producer-canonical self-digest probes passed, and the focused terminal,
    control, and verifier gate passed 18 tests in 75.83 seconds. No
    implementation or test source changed, so the long commit gate and fresh
    gameplay validation were not applicable.
    Cross-fitted and legacy gradients differ materially, but card-reward
    greedy behavior remains near-saturated: `take` is the maximum family for
    1,773 of 1,774 final-window multi-family decisions. Also preserve the 2,261
    lower-bound-clipped baseline predictions as an unresolved support signal.
    No evaluation cohort or production checkpoint was accessed, no victory was
    observed, and all policy-quality, causal, formal-RL, gameplay,
    CommunicationMod, qualification, and promotion claims remain false. Do not
    start an immediate successor. The next gate is a source-only read-only
    baseline-support and card-reward attribution audit over the sealed r2
    artifacts.
55. Preserve the completed source-only cross-fitted baseline-support audit and
    its bounded
    `take_pressure_persists_on_supported_unclipped_rows` verdict. Plan commit
    `c0ad75a297913755f5084e9c6439c18bda6d9c09` and source commit
    `4734ac87705f94b261a69d797ef50805060d4163` were pushed before analytical
    publication. Two fresh isolated processes independently verified the
    unchanged sealed r2 bundle and produced byte-identical reports: JSON
    SHA-256
    `0f63681aea43e197bba0d5fcd8b0a6f759c4fe27a3646a6648b2cbad87d968c0`
    and Markdown SHA-256
    `43e566dd5d838ae5710adfaac52d276a9c1a1e469e697a663c2341a0aa98dd7e`.
    Across 11,729 decisions, 2,261 predictions were clipped low and 9,468
    remained unclipped. Among 3,536 multi-family card rewards, the supported
    direct take-logit pressure was positive for both clipped rows
    (`0.00022624620570936817`) and unclipped rows
    (`0.009512804533328175`); every supported final-window unclipped chunk was
    also positive. The exact final-window concentration remained 1,773
    greedy `take` rows and one `bowl` row at `seed-2663:decision-56`, while the
    immutable saturation predicate remained false. Lower-bound clipping is
    therefore not a sufficient explanation for the remaining direct `take`
    pressure. This is descriptive mechanism evidence, not proof that accepting
    cards is wrong or that the policy is valuable.
    Focused audit tests passed 34 tests in 1.01 seconds; the audit plus existing
    independent-verifier boundary passed 157 tests with one skip in 423.81
    seconds. The repository `commit` gate passed 4,638 tests with 18 skips in
    1,270.15 seconds, 1,273.82 seconds including orchestration. Fresh gameplay
    validation was not applicable because no live behavior changed. All
    training, replay, evaluation, OPE, model/native loading, gameplay,
    CommunicationMod, qualification, promotion, policy-quality, causal, and
    formal-RL authority remains false. The next gate is a separately reviewed
    source-only proposal that distinguishes supported card acceptance from
    conditional card-choice collapse with synthetic contracts and shared-
    gradient diagnostics; it must not authorize another empirical run by
    itself.
56. Preserve the 2026-08-09 pytest gate requalification as the current
    bounded-feedback baseline. The prior inclusive `commit` boundary passed
    4,638 tests with 18 skips but required 1,273.82 seconds including
    orchestration. Fresh attribution isolated the cross-fitted verifier at
    about 422.8 seconds, seven lifecycle/control files at 320.32 seconds, and
    the remaining material historical replay and fresh-process nodes from a
    502.59-second remainder. The manifest now contains 15 documented
    whole-file `full_only` entries: the two existing outcome-evidence files
    plus 13 measured evidence, lifecycle, replay, and verifier files. All
    unlisted tests remain inclusive by default, and changing an excluded file
    or source it specifically owns requires direct focused validation.
    Runner regressions passed 39 tests in 1.88 seconds. The finalized
    `commit` profile passed 3,593 tests with 16 skips in 281.23 seconds of
    pytest, 284.75 seconds including orchestration, leaving 15.25 seconds of
    margin under the unchanged five-minute ceiling. The unchanged `full`
    profile then passed 5,353 tests with 18 skips in 2,283.45 seconds of
    pytest, 2,287.43 seconds including orchestration, with no exclusions. Each
    final profile was invoked once and was not retried for duration. No test
    body, runner, pytest configuration, production code, gameplay, simulator,
    or RL behavior changed. A later conforming `commit` run above 300 seconds
    invalidates this timing qualification until another measured
    requalification succeeds. The RL next gate remains a separately reviewed
    source-only proposal distinguishing supported card acceptance from
    conditional card-choice collapse.
57. Preserve the 2026-08-09 r2 pytest gate requalification as superseding item
    56. The next conforming `commit` invocation had invalidated item 56's
    bounded-feedback claim: it reported 3,638 passes, 16 skips, and one runtime
    deadline failure in 300.24 seconds of pytest, 303.60 seconds including
    orchestration, and was not retried. The deadline defect was repaired in
    separate commit `35b4249c0`; the complete runtime file then passed 24 tests
    in 16.14 seconds. The only test delta since item 56 is the pending 46-test
    card-acceptance audit, which passed directly in 7.39 seconds. Excluding it
    alone predicts only 3.79 seconds of margin; also excluding the sole failed
    runtime owner predicts 19.93 seconds, above item 56's prior 15.25-second
    margin. The frozen 17-file candidate passed 39 runner tests in 1.53 seconds,
    emits exactly 17 `commit` ignores, and leaves `full` unchanged. The final
    `commit` then passed 3,571 tests with 16 skips in 259.47 seconds of pytest,
    262.89 seconds including orchestration, leaving 37.11 seconds below the
    unchanged ceiling. Unchanged `full` passed 5,401 tests with 18 skips in
    2,248.44 seconds of pytest, 2,252.15 seconds including orchestration. Both
    were invoked exactly once; neither was retried and no later exclusion was
    added. Fresh gameplay validation is not applicable.
58. Preserve the completed card-acceptance-versus-conditional-choice audit and
    its bounded
    `acceptance_pressure_with_conditional_concentration_but_mixed_direct_pressure`
    verdict. Plan commit `aaea73c0c`, source commit `60275dd34`, and publication
    source identity `d70a98f97a4f193bfd59c85c5d3b227d74518ec7` were pushed
    before analytical publication. Two fresh isolated source-only processes
    independently verified the unchanged sealed r2 bundle and produced byte-
    identical reports: JSON SHA-256
    `0a10f7e763a40d7a6de751abaa6ac3aa13e02bace06ff6453fd79942d2447f33`
    at 56,923 bytes and Markdown SHA-256
    `3a789e7924bdf2de55c2e27c98dfefeffb0ef58334dc7cd410f31c243af85825`
    at 1,877 bytes. Exact reconstruction retained 11,729 decisions, 512
    trajectories, and all 3,536 eligible card rewards; 3,522 rows had three
    take candidates and 14 had four. Acceptance pressure was positive in all
    eight chunks. Mean normalized take entropy strictly declined from
    `0.99997064045` to `0.99986125183`, while mean top-two conditional gap
    strictly increased from `0.00274131737` to `0.00596556638`. Direct
    conditional greedy-margin pressure remained mixed in the final window,
    with chunk sums `-0.00040437431`, `0.00181875185`, `-0.00144275997`, and
    `0.00129044526`. All gradient clip factors were one; exact shared-gradient
    geometry remains non-causal because no per-row score Jacobian was retained.
    Audit tests passed 46 tests in 7.39 seconds; the final runtime/audit/runner
    focused set passed 109 tests in 25.95 seconds. The requalified `commit`
    and unchanged `full` results are recorded in item 57. Fresh gameplay
    validation was not applicable. Every training, replay, evaluation, OPE,
    model/native loading, gameplay, CommunicationMod, qualification,
    promotion, policy-quality, causal, and formal-RL authority remains false.
    The next gate is a separate source-only acceptance-coordinate objective-
    intervention proposal. It must preserve conditional card-choice support,
    compare explicit synthetic invariants and existing-row counterfactual
    gradients, select no coefficient or model by this audit alone, and grant
    no fitting, training, empirical execution, evaluation, or promotion.
59. Preserve the completed card-acceptance objective-intervention audit and its
    bounded `bounded_conditional_conflict_guard_feasible` verdict. Planning
    commits `cdab3570f` and `f3a9bd6e1`, source commits `38cc9bb42` and
    `82369c749`, the single-owner verifier repair `0f3f042d0`, and publication
    source identity `30e9a558013e5733059e9beaf64b1e42fc5c983c` were pushed
    before the successful publications opened sealed evidence. The first
    publication pre-start exposed a non-reentrant double lease lock and wrote
    no output; the repaired source retained the verifier's complete owner-
    liveness, execution-identity, and stable-path checks under one held lease.
    Two fresh isolated source-only processes then produced byte-identical
    reports: JSON SHA-256
    `c30160cab6bd39a3f93ee65235f432642f8988d5e6dae17b2473d73c9a757156`
    at 73,889 bytes and Markdown SHA-256
    `16628decc23c013de0cf174ed8b6dbcc8e4c243ebd00e54e7d9325d3f93f0aa3`
    at 1,755 bytes. All eight chunks retained conditional support. Recorded
    family/conditional gradients conflicted only in chunks 1 and 4; the fixed
    guard projected those dots to numerical zero and left every non-conflicting
    chunk unchanged. Family-policy ablation and conditional-conflict guarding
    remain descriptive counterfactuals: the audit ranks neither, estimates no
    policy value, and selects no objective, coefficient, architecture,
    successor, or policy. The focused audit passes 38 tests and the adjacent
    audit boundary passes 84. The one `commit` gate was not green: it reported
    3,601 passes, 16 skips, and one test-order isolation failure in 294.13
    seconds; the failed node and focused boundary were repaired without
    retrying that gate. The unchanged `full` gate passed 5,439 tests with 18
    skips in 2,357.70 seconds of pytest, 2,361.43 seconds including
    orchestration. Fresh gameplay validation was not applicable because no
    live behavior changed. Every training, replay, evaluation, OPE,
    model/native loading, gameplay, CommunicationMod, qualification,
    promotion, policy-quality, causal, and formal-RL authority remains false.
    The next gate is a separate OpenSpec proposal for an independent acceptance-
    coordinate objective and architecture contract. It must choose an explicit
    testable design, preserve conditional choice, define canary/holdout and
    rollback criteria, and grant no empirical execution until separately
    reviewed and authorized.
60. Preserve the completed source-only card-acceptance objective architecture
    contract. Planning commits `a3e2edc70` and `9909abe49` fixed the reviewed
    public API, report schema, authority inventory, and future empirical-entry
    boundary before implementation. Source commit `23051ad5a` adds two
    independent public `StateConditionedCandidateRanker` instances with exact
    `family_head.*` and `conditional_ranker.*` checkpoint namespaces. Exact
    candidate kinds remain separate, including `take`, `skip`, and `bowl`;
    family features use canonical float64-accumulated means with checked
    float32 conversion, and the active acceptance coordinate is
    `z_take - logsumexp(all explicit non-take family logits)` in float64.
    Selected family terms update only the family head, selected conditional
    terms and unweighted per-family entropy update only the conditional head,
    and expected conditional plus joint entropy remain explicitly cross-head.
    The six registered synthetic fixtures execute rather than serving as
    labels, all 12 published invariants pass, and report construction preserves
    caller RNG state. Two fresh isolated processes produced byte-identical
    canonical reports: JSON SHA-256
    `244bbfd045f901d2f1302d1976d1618d9725c56d8d86db22dd207c2724d792e1`
    at 5,113 bytes and Markdown SHA-256
    `8cd16e1943e6e46c41e3f2c95714ee3ab13c4ab4e2efb74667d0bce6a269234e`
    at 1,088 bytes. The final focused suite passes 42 tests; the direct legacy
    preservation boundary passes 107. The single `commit` gate is correctness-
    green with 3,651 passes and 16 skips in 296.62 seconds of pytest, but its
    300.29-second total exceeds the qualified five-minute feedback ceiling by
    0.29 seconds and therefore invalidates timing qualification without
    authorizing a retry or post-result exclusion. The unchanged `full` gate
    passes 5,481 tests with 18 skips in 2,339.93 seconds of pytest, 2,343.85
    seconds including orchestration; all strict OpenSpec validation passes
    80/80 and final independent review has no P1/P2. Fresh gameplay validation
    is not applicable because existing runtime, experiment, checkpoint,
    production agent, and CommunicationMod imports remain unchanged. Every
    architecture/objective choice beyond this contract, fitting, training,
    replay, evaluation, OPE, model/native loading, seed access, gameplay,
    qualification, promotion, policy-quality, causal, and formal-RL authority
    remains false. A future empirical successor requires a separate OpenSpec
    change and execution authorization with new frozen candidate/control
    identities, candidate disabled by default, one at-most-once 128-pair
    structural canary, one untouched 512-seed paired holdout, and exact rollback
    to the registered control. It must separately choose initialization, loss
    coefficients, optimizer, cohort, and policy-quality thresholds.
61. Preserve the r6 card-acceptance empirical successor as a terminal
    infrastructure failure with no learning evidence. Its one logical training
    identity stopped before native loading, environment construction, seed
    access, checkpoint publication, or optimizer work because the registered
    zero-byte `analysis_scripts/__init__.py` package marker was rejected by a
    generic positive-size source binding. Independent terminal verification
    reconstructed zero accesses and updates, verified rollback to the control,
    and kept candidate, canary, holdout, qualification, promotion, gameplay,
    and production authority false. Do not retry r6 or reinterpret it as a
    policy result. The immediate lane is a focused zero-byte source-binding
    repair followed by a new exploratory smoke-training identity. Exploratory
    runs may be repaired and repeated under new attempt identities; frozen
    no-retry cohorts, complete independent review, and full qualification gates
    are deferred until a usable model candidate exists. Allocate routine effort
    primarily to training and result analysis, use focused tests for concrete
    blockers, and reserve full gates and independent review for shared-risk or
    qualification boundaries.
62. Preserve the completed two-step conservative combat-RL progression and its
    production milestone. The second single-step SGD candidate at SHA-256
    `edf7d33124a3fbbc3abee6bae6c7b9654ea9a9191dcf151e5c0b000c71a4f454`
    improved SmoothL1 on both fresh r5 and r6 parent-policy replay, retained at
    least `99.8898%` parent action agreement, and passed its 20-pair live gate
    with one candidate floor win, zero parent wins, 19 ties, and no progression
    regression. It is now the promoted production baseline. Its subsequent r7
    zero-update collection completed all 20 registered seeds, reached 497 total
    floors, entered Act 3 twice, and produced one AI-marked A0 Ironclad victory
    on floor 51. This is the first victory from a promoted production baseline
    and the second known AI-marked Ironclad victory overall; the historical
    first came from an unpromoted candidate. The original first-victory north
    star is complete. The next combat objective is repeatable victory and Act 3
    coverage rather than another isolated first win. The r7 terminal checkpoint
    observed 4,194 source transitions but stored only the newest 4,096, so it is
    a fixed one-use truncated-tail holdout, not a complete replay. Use consumed
    r5 and r6 replay for one bounded multi-update successor, freeze it before
    evaluating once on r7, and do not fit, select, reconstruct, or tune against
    r7. Keep routine effort centered on model fitting, trajectory collection,
    and result analysis; use focused tests only for concrete blockers and reserve
    broad review for an actual promotion boundary.
63. Preserve the completed r10 and r11 successor results as complementary
    negative evidence. The low-rate r10 candidate improved frozen replay loss
    but all 20 live floor pairs tied, proving its update was too small to create
    observable value. The stronger-TD r11 candidate also improved development
    and fresh-holdout SmoothL1 with `99.6685%` parent action agreement, but its
    matched live gate lost the sole non-tied pair: zero candidate wins, one
    parent win, 19 ties, and a `-6` summed floor delta. In that pair, the first
    trace-visible action difference was a turn-4 Slime Boss target choice; the
    candidate then entered a worse multi-enemy split state and died on floor
    16, while the parent cleared the boss and reached floor 22. Reject both
    candidates and retain the promoted r8 checkpoint. Do not answer this result
    by further increasing one-step TD weight. The next candidate must use a
    sequence- or outcome-aware objective and demonstrate a general supported-
    trajectory benefit before consuming another fresh live holdout.
64. Preserve r12 as a sequence-aware offline negative. Its full-combat-return
    candidate improved both full-return and one-step SmoothL1 on development
    replays r6 and r8, then repeated both loss improvements on the untouched r9
    production replay with `99.3748%` parent agreement. It still failed the
    registered behavioral guards: off-target disagreement was `1.0848%` versus
    a `1%` ceiling, and positive-energy End Turn count rose by eight versus an
    allowed increase of one. A read-only diff found 23 changed greedy actions,
    including nine new positive-energy End Turns and one change away from a
    parent positive-energy End Turn. Reject r12 without a live gate and retain
    r8 in production. R9 is consumed; do not retry it, shrink interpolation, or
    tune thresholds after observing it. The next training candidate may use r7
    for fitting and r6/r8/r9 as development evidence, but must put a direct
    parent non-End-over-End preservation term into the training objective and
    pass the same cross-cohort loss and behavior guards before another fresh
    replay is collected.
65. Preserve r13 as the first full-return candidate to close r12's End Turn
    boundary on all consumed development evidence. It adds a direct loss that
    preserves the promoted parent's positive-energy non-End-over-End margin,
    fits on r7, and validates on r6, r8, and consumed r9. The fixed weight sweep
    selected the smallest passing positive weight, `0.25`; weight zero exactly
    reproduced r12's r9 failure, while every positive weight passed all three
    replays. The selected candidate improves full-return and one-step loss on
    every replay, retains at least `99.3880%` parent action agreement, keeps
    off-target disagreement at or below `0.5424%`, and reduces positive-energy
    End Turn count on each replay. It is frozen at SHA-256
    `b05bbb904bee075628691565de98fbdc119bbae0fc2cc2e41e55acd5084bafe7`
    for one untouched production-policy replay confirmation only. It has no
    live-evaluation or promotion authority.
66. Preserve r10 as the consumed fresh confirmation cohort for r13. Its first
    launch completed no game and published no checkpoint before Windows logged
    a native `python.exe` crash in `nvcuda64.dll` (`0xc0000409`). A minimal CUDA
    health check passed, after which one exact recovery with the same committed
    config, parent checkpoint, and seed order completed all 20 games. The
    terminal replay contains all 3,081 transitions, has no optimizer state or
    loss, and keeps online and target weights exactly equal to production r8.
    Frozen r13 then passed its single confirmation: full-return loss
    `54.72178 -> 54.70110`, one-step loss `4.43178 -> 4.41149`, parent agreement
    `99.6430%`, off-target disagreement `0.5305%`, and positive-energy End Turn
    `1624 -> 1621`. The raw confirmation has a descriptive full-SHA typo after
    the correct `38b80ac9f` prefix; preserve it unchanged with the published
    erratum and do not rerun. R13 is eligible for one separately registered
    matched live gate, not automatic promotion.
67. Preserve the r13 matched live gate as a clean all-tie negative. Candidate
    and production r8 completed all 20 shared seeds without native recovery or
    policy runtime failure and produced the identical floor vector, 439 total
    floors, ten Act 2 entries, four Act 2 boss reaches, zero Act 3 entries, and
    zero victories. Candidate paired wins and parent paired wins were both zero;
    all 20 pairs tied. The preregistered non-tie requirement therefore failed
    and r13 is not promoted. This shows the `alpha=0.5` trust-constrained return
    update is behaviorally safe but too small to create observable live value.
    Do not rerun or tune against this cohort. Keep the direct End Turn trust
    constraint and use consumed replay to investigate a larger effective step,
    with r6/r8/r9/r10 all required to pass before another fresh holdout.
68. Preserve r14 and r15 as the bounded step-size follow-up. The full-step r14
    update improved full-return and one-step losses everywhere and its trust
    term removed new positive-energy End Turns, but no weight passed all four
    replay guards because parent agreement and off-target disagreement crossed
    their fixed boundaries. Do not admit it by adding more trust weight or
    weakening thresholds. The intermediate `alpha=0.75` r15 candidate selected
    trust weight `0.25` and passed r6/r8/r9/r10: at least `99.2389%` parent
    agreement, at most `0.7396%` off-target disagreement, lower positive-energy
    End Turn count on every replay, and improvement in both losses. Freeze SHA-
    256 `fcef143b8387fcee27e5f29cd53283e509cc5fbd3eec5c6b77cdebbdf4645b73`
    for one fresh production-r8 replay confirmation only. It has no live or
    promotion authority.
69. Accept r11 as the fresh replay confirmation for frozen r15. Production r8
    completed all 20 registered seeds naturally with 4,154 source transitions;
    the fixed replay capacity retained the latest 4,096, matching the registered
    horizon. Frozen r15 improved full-return SmoothL1 from `43.2584` to
    `43.2173` and one-step SmoothL1 from `3.90355` to `3.87839`, retained
    `99.2188%` parent agreement, limited off-target disagreement to `0.8314%`,
    and reduced positive-energy End Turns from 2,018 to 2,004. It is eligible
    for one separately registered 20-pair matched live gate, not promotion.
    Preserve the raw confirmation and its provenance erratum; do not rerun or
    tune against r11.
70. Accept the r15 matched live gate as passed while keeping promotion a
    separate decision. On 20 new shared seeds, r15 beat production r8 on one
    floor pair, lost none, and tied 19; total floors were 478 versus 475. R15
    also entered Act 2 11 times versus 10, while both arms reached the Act 2
    boss seven times, entered Act 3 once, and won no runs. The sole divergence
    followed an identical path through floor 16: r8 died to The Guardian while
    r15 cleared it and reached floor 19. Both arms completed naturally without
    runtime failures. This supports only a conservative baseline replacement,
    not a large live-effect or win-rate claim.
71. Promote frozen r15 as the bounded production combat baseline. The production
    command remains evaluation-only, epsilon zero, conservative routing, and
    capped at five games per launch. Keep the prior r8 production config as the
    exact rollback artifact. The evidence supports a low-risk replacement only:
    19 of 20 live pairs tied and neither arm won. For the next iteration, spend
    the first work on a bounded successor fit using consumed r11 and older
    consumed replay; collect a new promoted-r15 holdout only after that successor
    passes the fixed cross-replay guards.
72. Freeze r16 as the first promoted-r15 successor for one fresh replay only.
    It used eight full-gradient SGD updates on consumed r11, selected trust
    weight `0.25` at interpolation `alpha=0.5`, and moved `6.9547e-6` relative
    L2 from r15. It improved both registered losses on r6/r8/r9/r10 while
    retaining at least `99.2465%` parent agreement, at most `0.9270%`
    off-target disagreement, and fewer positive-energy End Turns on every
    replay. Do not fit or tune against the next fresh promoted-r15 replay.
73. Accept r12 as the single fresh replay confirmation for frozen r16.
    Production r15 completed all 20 registered seeds naturally with 3,688
    complete, untruncated transitions. Frozen r16 improved full-return SmoothL1
    from `44.3240` to `44.2993` and one-step SmoothL1 from `4.17212` to
    `4.15476`, retained `99.4035%` parent agreement, limited off-target
    disagreement to `0.5747%`, and reduced positive-energy End Turns from 1,815
    to 1,804. It is eligible for one separately registered 20-pair matched live
    gate against production r15, not automatic promotion. Do not rerun or tune
    against r12.
74. Accept the r16 matched live gate as passed while keeping promotion a
    separate decision. On 20 new shared seeds, r16 beat production r15 on one
    floor pair, lost none, and tied 19; total floors were 493 versus 476. R16
    also entered Act 2 13 times versus 12 and reached the Act 2 boss seven
    times versus six, while neither arm entered Act 3 or won a run. The sole
    divergence followed the same path and non-combat choices through floor 16:
    r15 died to Slime Boss while r16 cleared it with 22 HP and reached floor 33.
    Both arms completed naturally without runtime failures. This supports only
    a conservative baseline replacement, not a large live-effect or win-rate
    claim.

## Work Lanes

The active lane is bounded combat-RL policy improvement. R13's half step was
safe but tied production on all 20 live pairs; r14's full step was too broad;
r15's three-quarter step passed consumed r6/r8/r9/r10, its single fresh r11
confirmation, and a 20-pair live gate by one floor pair with no losses. It is
now the bounded production baseline, with r8 retained as rollback. R16 passed
the consumed cross-replay guards, its single fresh r12 confirmation, and a
20-pair matched live gate by one floor pair with no losses. The immediate next
step is a separate conservative promotion decision that retains r15 as exact
rollback. The near-term measure remains repeatable Act 3 and victory coverage,
not whether another one-off favorable pair can be found.

The non-combat card-acceptance lane remains paused at its r6 zero-byte
source-binding infrastructure failure. Resume it only as a separately
prioritized exploratory training lane; do not let its former full review and
qualification process displace the active combat fitting and evaluation loop.

The offline production candidate-schema fix, anti-retry review, r2 successor,
potion, relic, and card-cost identity repairs, post-repair Current baseline
study, and unique final Current replication are complete. The original study
remains a terminal blocked result after 18 partial canary rows. The final
replication passed its 16-pair canary but retained only five of 64 holdout
pairs, then failed terminal publication. Neither result establishes a baseline
floor. Current is no longer eligible for the same baseline question. Formal RL
remains `no_go` because baseline policy and source-comparable target-supported
outcomes are still blocked.

Do not modify, retry, or reinterpret either consumed baseline attempt. The
single post-final-repair replication authorized by the narrowed anti-retry
rule is now closed. The baseline-strategy decision does not select another
quality comparator: it separates a frozen experimental control from a credible
policy baseline. Bottled and SimpleAgent remain auxiliary-only, while
source-comparable target-supported outcomes remain an independent prerequisite
for formal RL and live-value claims. The card metadata cost audit and its
bounded compatibility repair are closed. The r1
simulator-only experiment remains a terminal native-load failure with no seed
access. Its r2 successor completed exactly once and is valid simulator evidence:
the trained policy improved terminal floor against seeded initialization on
both canary and holdout, but produced no victory improvement and therefore no
registered learning signal. Formal RL remains `no_go`; the result grants no
Current loading, policy promotion, or replacement experiment. The r2 terminal
postmortem is complete and sets an immediate r3 to `no_go`: the registered
linear feature composition cannot use shared state to change candidate order,
and the final policy saturated to taking every observed card reward. The
state-conditioned ranker, policy-input boundary, and anti-collapse diagnostic
capabilities were integrated into one terminal simulator experiment. Exact API
v3 state and candidates remained separate through scoring, but the trained
canary policy collapsed to always taking card rewards and stopped before
holdout. The experiment is consumed and grants no successor run. The completed
read-only trajectory audit locates persistent greedy collapse at training chunk
`2`, observes candidate multiplicity plus learned probability amplification,
and leaves causal intervention claims unresolved. The Current comparator
evidence lane is closed with
`no_viable_baseline_candidate`; there is no active empirical baseline
execution. The action-family source-only design, additive distribution,
frozen-score counterfactual audit, and hierarchical objective-terms contract
are complete. The contract preserves selected family plus conditional log
    probability, separately observable entropy terms, and raw-score deterministic
    evaluation without choosing a coefficient or loss. The hierarchical
    successor then completed exactly once and stopped during training after its
    registered card-reward family-saturation gate fired. Near-maximal family
    entropy preserved stochastic exploration but did not prevent a consistent
    greedy `take` sign from widening over eight chunks. No canary or holdout seed
    was accessed, and the terminal bundle grants no policy-quality, formal-RL,
    target-supported-outcome, loading, gameplay, qualification, or promotion
    authority. The source-only credit-assignment audit is complete: direct
    take-logit pressure aligns in aggregate but is heterogeneous in the
    supported effective-floor `17..33` band. The additive hierarchical
    advantage-attribution contract now closes the immediate source-only design
    gap with trajectory-disjoint provenance, exact shared-gradient component
    accounting, and uniform clipping evidence. The cross-fitted hierarchical
    successor was authorized and consumed exactly once, but repeated full
    registration validation allowed only 11 completed accesses before the
    fixed wall-time gate. Its valid terminal failure contains no complete chunk
    or mechanism evidence and cannot be resumed or retried. The source-only
    control-plane repair now closes the known validation-throughput,
    elapsed-charge, terminal-publication, and true-child-liveness defects. It
    does not retroactively create mechanism evidence or authorize a retry. The
    first one-shot readiness audit remains terminal `no_go_source_binding`; its
    source identity was not reused. Later source-only repairs and readiness
    audits culminated in the independently verified r5 `go`, followed by the
    exact compact 20260808-r2 registration, execution request, standing
    delegation, delegated approval, tracked authorization, and one terminal
    execution. The independently verified run completed all 512 primary
    episodes and eight updates without resume. Cross-fitted attribution changed
    the gradient materially relative to the legacy objective, but card-reward
    greedy behavior remained near-saturated at 1,773/1,774 `take` maxima in the
    final window, 2,261 baseline predictions were clipped at zero, and no
    victory or evaluation evidence was observed. The source-only audit in item
    55 then found supported positive direct `take` pressure on both clipped and
    unclipped rows and in every final-window chunk, so lower-bound clipping is
    not a sufficient explanation for the concentration. Item 58 now separates
    that consistent acceptance coordinate from conditional card-choice
    concentration: concentration progressed monotonically, but final-window
    direct conditional margin pressure remained mixed. Item 59 now shows that
    a fixed conflict projection is geometrically feasible only as a descriptive
    counterfactual; it does not select an objective or predict policy value. Do
    not start an immediate empirical successor. First review a separate
    acceptance-coordinate objective and architecture proposal with explicit
    canary, holdout, rollback, and authority boundaries. Until that gate passes,
    do not load a production model, evaluate, run OPE, launch gameplay or
    CommunicationMod, qualify, promote, or infer policy quality or causal value
    from mechanism completion alone.

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
- For a one-attempt Windows evidence run that atomically publishes files, do
  not read any file under its active output root while the process is alive.
  Monitor process liveness only, then inspect artifacts after process exit.
- Do not treat an outer shell, wrapper timeout, or waiting-cell exit as proof
  that the evidence process ended. Confirm the true Python child is absent and
  its exclusive lease is no longer locked before reading the output root.
- Independent verification of an output root with a stale lease must acquire
  that lease non-blockingly and hold it across the complete evidence inventory
  and validation. A locked, live-owner, malformed, or ambiguous lease blocks
  before any terminal evidence is read.
- Treat the latest 2026-08-07 `commit` gate result of 4,434 passed, 17 skipped,
  657.01 seconds of pytest, and 659.89 seconds including orchestration as
  confirmation of timing drift: correctness passed, but the qualified
  five-minute feedback bound was exceeded by 359.89 seconds. This change
  invoked the gate exactly once and did not rerun it because of duration;
  schedule a separate read-only duration audit before claiming the bounded-
  feedback requirement remains met.
- Treat the 2026-08-08 readiness `commit` gate as executed once but not green:
  4,490 tests passed, 18 skipped, and two unchanged runtime tests failed after
  796.44 seconds of pytest (799.96 seconds including orchestration). Both
  failures are exact-ceiling floating-point deadline checks in files outside
  the readiness diff. The gate was not rerun and the runtime files were not
  changed under the source-only readiness scope.
- Treat the 2026-08-08 readiness source-binding repair `commit` gate as invoked
  exactly once but not green: 4,514 tests passed, 18 skipped, and one unchanged
  cross-fitted runtime test failed after 815.11 seconds of pytest (819.01
  seconds including orchestration). The failure is the same exact-ceiling
  floating-point deadline boundary in a runtime and test outside the staged
  repair. The gate was not rerun and that unrelated runtime was not changed.
- Treat the 2026-08-08 compact-registration `commit` gate as invoked exactly
  once but inconclusive: the outer command timed out after 1,204.4 seconds
  before pytest returned a summary, and no Python child remained afterward.
  The gate was not rerun. This is a test-infrastructure and feedback-duration
  failure, not RED test evidence; the complete scoped control, seed-inventory,
  preservation, readiness, and independent-verifier files remain green as
  recorded in direction item 45. Include this result in the separate read-only
  test-duration audit before changing test tiers or timing limits.
- Treat the 2026-08-08 readiness artifact-boundary repair `commit` gate as
  invoked exactly once but inconclusive: the outer command timed out after
  904.4 seconds with exit 124 before pytest returned a summary. The exact
  runner and pytest child remained alive after the timeout, were terminated by
  PID, and were confirmed absent. The gate was not rerun. This is test-
  infrastructure and feedback-duration evidence, not RED test evidence; the
  final 119-test focused source-only suite, strict OpenSpec validation, Python
  compilation, and independent review remain green as recorded in direction
  item 47.
- Treat the 2026-08-09 baseline-support audit `commit` gate as green but too
  slow for routine feedback: 4,638 tests passed with 18 skips in 1,270.15
  seconds of pytest, 1,273.82 seconds including orchestration. The gate was
  invoked once and was not followed by the `full` profile. Include its runtime
  attribution in the separate read-only test-duration audit before changing
  test tiers, test selection, or timing limits.
- Treat the 2026-08-09 r2 tiered-gate requalification as the current timing
  baseline: `commit` passed 3,571 tests with 16 skips in 259.47 seconds of
  pytest, 262.89 seconds including orchestration, and unchanged `full` passed
  5,401 tests with 18 skips in 2,248.44 seconds of pytest, 2,252.15 seconds
  including orchestration. The 17-file boundary requires direct coverage for
  excluded ownership; any later over-ceiling invocation invalidates timing
  qualification without authorizing a retry or post-result exclusion.
- Treat the 2026-08-09 card-acceptance architecture `commit` gate as
  correctness-green but no longer timing-qualified: 3,651 tests passed with 16
  skips in 296.62 seconds of pytest and 300.29 seconds including orchestration,
  exceeding the five-minute total ceiling by 0.29 seconds. It was invoked once
  and was not retried. Include this result in the next separate read-only
  duration audit before changing tiers, targets, or limits; the unchanged
  `full` result remains 5,481 passed, 18 skipped in 2,339.93 seconds of pytest
  and 2,343.85 seconds including orchestration.

Historical reports and archived changes retain the objectives and authority
boundaries that applied when they were written. This document is the canonical
source for the current project phase.
