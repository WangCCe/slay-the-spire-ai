# Project Direction

Last updated: 2026-08-07

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

## Work Lanes

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
    subsequent one-shot readiness audit closed at `no_go_source_binding`
    because its consumed-schedule contract omitted three bound provenance
    fields. The source-only schema and durable main-spec binding correction is
    now complete, reviewed, pushed, synced, and archived without invoking the
    auditor. The next gate is a separate source-only eligibility and
    preregistration review for at most one fresh readiness publication against
    a new pushed clean identity. Until that change fixes the audit id, attempt,
    output and scratch paths, non-retry proof, ceilings, and exact command, do
    not invoke readiness or treat the correction as empirical registration or
    execution authority. Do not fit or load another model, access a fresh seed,
    make a causal or OPE claim, change an estimator or reward, or infer
    execution authority from either the repair closeout, failed readiness
    attempt, or source-only correction.

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

Historical reports and archived changes retain the objectives and authority
boundaries that applied when they were written. This document is the canonical
source for the current project phase.
