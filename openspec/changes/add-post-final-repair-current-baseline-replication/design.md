## Context

Formal non-combat RL readiness still fails two independent domains: a credible
non-teacher baseline floor and source-comparable target-supported outcomes.
Current is the only eligible non-teacher comparator. Its integrated baseline
study consumed seeds `11000..11008` and stopped before a complete canary on the
bridge's `Injury` metadata representation. The registered holdout
`12000..12063` remained untouched, but both cohorts and the execution identity
are permanently historical.

The later source-complete repair covers exactly 20 empty-cost `Unplayable.`
card identities. Together with the reachable-event, shop sentinel/support,
candidate-schema, potion, card, and relic audits, it closes every known static
bridge boundary. Current's policy sources, first-candidate control, thresholds,
bootstrap, and limits did not change after the consumed preregistration. The
remaining uncertainty is empirical: another reachable snapshot could still
expose an unknown structural boundary.

The current baseline-readiness spec makes every blocked integrated study a
permanent answer to the policy-quality question. That prevents opportunistic
retries, but it also conflates a pre-quality measurement defect with a complete
negative quality result. This change introduces one narrow project-level
exception without making structural repair loops generally retryable.

## Goals / Non-Goals

**Goals:**

- Define one final, independent Current-versus-first-candidate replication that
  can establish or reject a credible simulator baseline floor.
- Preserve every consumed artifact and seed while proving that no observed
  partial result changes policy, thresholds, support rules, or cohort choice.
- Fix the cohort selection algorithm, gates, replay, limits, lifecycle, and
  publication contract before any native loading or seed access.
- Make source-only validation repeatable and make the empirical execution
  terminal only from its durable started journal onward.
- Ensure any result in the final replication ends the Current-baseline lane.

**Non-Goals:**

- No Current heuristic or priority change, SimpleAgent/Bottled comparison,
  reward change, model fitting, RL training, gameplay, Communication Mod work,
  OPE, qualification, loading, or promotion.
- No reinterpretation, continuation, seed reuse, or artifact rewrite for the
  consumed baseline study.
- No generic retry framework and no permission for a second replication after
  the proposed successor.
- No claim that a simulator floor supplies target-supported outcome evidence.

## Decisions

### Add a new versioned runner and preserve the consumed runner

Implement `analysis_scripts/noncombat_current_baseline_replication.py` as a
new publication identity. It composes the existing API v3 adapter,
`CurrentPolicyBridgeSession`, metadata/event contracts, tracked-seed inventory,
and canonical hash/JSON helpers. It may reuse pure predecessor behavior but
must not change the consumed runner, registration, journal, rows, metrics,
bootstrap placeholder, report, or manifest.

The new registration binds the complete predecessor terminal identity, the
post-repair readiness review, the exact closure evidence required by that
review, the current policy and bridge sources, and all external runtime/native
identities. A fresh-process verifier reconstructs canonical outputs without
importing the native module.

Alternative: edit and rerun the old runner. Rejected because its identity and
cohorts are consumed and its terminal artifacts must remain byte-identical.

Alternative: run another structural diagnostic first. Rejected because it
would continue the diagnostic loop without answering the floor question.

### Narrow anti-retry by evidence phase

The readiness rule distinguishes three cases:

1. A structurally complete canary or holdout that fails a quality, coverage,
   support, or bootstrap gate is terminal evidence. No replacement follows.
2. The historical study's exact incomplete `card_metadata_cost_invalid:
   Injury` failure can support one successor because the defect is closed by a
   source-complete audit and red/green regression, the policy and control are
   unchanged, thresholds are unchanged, partial rows do not enter a gate, and
   all consumed seeds are excluded.
3. The new successor is final. Any blocker, interruption after the started
   journal, canary stop, holdout failure, invalid publication, or positive
   result terminates the Current-baseline lane.

Repeatable source-only preparation and preflight do not create a journal,
construct an environment, or access a seed, so they are not empirical retries.
Once the runner writes its durable started journal, the identity is consumed
even if native loading fails before the first environment. This keeps the
empirical boundary simple and auditable.

Alternative: permanently block Current after any instrumentation failure.
Rejected because it converts a measurement defect into an unsupported policy
conclusion.

Alternative: allow a successor for every newly repaired structural defect.
Rejected because it recreates the patch-and-rerun loop and exposes fresh
cohorts to sequential selection.

### Fix a deterministic fresh-cohort algorithm before implementation

Fix `search_start = 60000`. At pushed preregistration, regenerate the tracked
seed inventory and choose the first 80 ascending integers at or above that
start that do not occur in the excluded set. Bind the exact resulting list in
the registration; assign the first 16 to canary and the remaining 64 to
holdout. Any overlap, duplicate, reordering, inventory drift, or changed
algorithm blocks preregistration rather than searching differently.

The proposal fixes the algorithm but does not materialize, reserve, or access
the exact cohort. The preregistration commit performs that deterministic step
after the source-only implementation is pushed. Historical `11000`/`12000`
cohorts, diagnostics, compatibility gates, and the reserved/consumed
`50000..51663` simulator experiment range remain excluded through the tracked
inventory and explicit lineage checks.

Alternative: choose a convenient untouched block during preregistration.
Rejected because discretionary selection after seeing historical results is
unnecessary.

Alternative: reuse the untouched old holdout. Rejected because it belongs to a
known consumed study design and its values are no longer a blind independent
successor cohort.

### Preserve the original comparator and numeric contract

Evaluate only frozen `current_optimized_ironclad_a0_conservative_snapshot_v1`
and `deterministic_first_candidate_control_v1`, each in fresh independent A0
Ironclad environments. SimpleAgent and Bottled provide no action, fallback,
label, reward, score, or pass criterion.

Canary remains 16 pairs with two replays per policy. It requires all four
Current categories, zero unexpected failures, at most one exact Courier
support row per policy, Current mean floor at least 15, and paired mean at least
0. Holdout remains 64 pairs with zero unexpected failures, all four categories,
at most three exact Courier rows per policy, Current mean at least 18, absolute
95% bootstrap lower bound at least 15, paired mean at least 3, and paired 95%
bootstrap lower bound greater than 0. Bootstrap remains 10,000 percentile
resamples with seed `20260803`.

Each episode permits at most 500 target decisions. Canary permits at most 600
seconds and 64 policy executions including replays; the complete attempt
permits at most 1,800 seconds and 320 policy executions. No runtime override is
accepted.

Alternative: raise or lower thresholds using the nine observed Current rows.
Rejected because those rows are incomplete structural evidence and any change
would introduce post-observation tuning.

### Retain exact support rows and every denominator

Only `unsupported_shop_courier_restock_semantics` may become a declared support
row. Both replays must stop at the same floor, decision coordinate, action
prefix, and reason. The row remains a non-victory at its last supported floor
in all absolute and paired metrics. Supported-only summaries are diagnostics
only. Every other bridge, adapter, native, mapping, mutation, legality,
determinism, resource, or publication failure blocks the final attempt.

Alternative: drop unsupported rows. Rejected because survivor-only metrics can
turn a narrower support envelope into an artificial quality improvement.

### Separate planning, implementation, preregistration, and execution

Planning is committed and pushed first. Source-only implementation then proves
red/green contract regressions, predecessor artifact preservation, no-native
verification, focused pytest, compilation, repository commit gate, and strict
OpenSpec validation. A later clean pushed preregistration materializes and
binds the cohort and external identities without importing native code.

Execution requires a separate tracked authorization artifact naming the exact
pushed registration hash and command. The runner writes the started journal
before native loading, runs canary once, and accesses holdout only if the
complete canary passes. The terminal artifacts are then verified without
native loading and consumed by a separate read-only readiness refresh.

## Risks / Trade-offs

- [Risk] Static closure misses another reachable representation. -> The final
  attempt fails closed and ends the Current-baseline lane; it does not trigger
  another successor.
- [Risk] The first-candidate control is weak. -> Mandatory absolute mean and
  bootstrap-lower-bound gates prevent relative improvement alone from passing.
- [Risk] Sixteen canary pairs are noisy. -> Canary is only a fixed stop gate;
  inferential floor checks use the untouched 64-pair holdout.
- [Risk] Fixing a search start reveals the selection algorithm before
  execution. -> The algorithm is outcome-independent, deterministic, and
  preferable to discretionary cohort choice.
- [Trade-off] Two policies and two replays require up to 320 policy episodes.
  This cost buys deterministic comparison and directly resolves the floor
  question if the bridge remains supported.

## Migration Plan

1. Commit and push proposal, design, delta specs, and tasks with no native or
   seed access.
2. Add red successor-contract tests and implement the new source-only runner
   plus no-native verifier without editing the consumed runner.
3. Verify historical artifact immutability, focused tests, compilation,
   repository commit gate, and strict OpenSpec; commit and push implementation.
4. On the pushed implementation, regenerate the tracked inventory, apply the
   fixed `60000` selection algorithm, bind exact cohorts and external
   identities, and commit/push preregistration without native import.
5. Stop for an exact execution authorization. If approved, execute the final
   canary and conditional holdout once, preserve the terminal result, and run a
   no-native verification and read-only readiness refresh.
6. Sync specs, archive the change, and push canonical closeout evidence.

Before a started journal, rollback may delete the unconsumed successor source
and registration. After a started journal, rollback preserves every successor
artifact and cannot create a replacement identity.

## Open Questions

None. Any request to change Current, the weak control, cohort algorithm,
thresholds, bootstrap, support semantics, replay, limits, or authority before
execution requires a new project-level decision and prevents this proposal
from running as written.
