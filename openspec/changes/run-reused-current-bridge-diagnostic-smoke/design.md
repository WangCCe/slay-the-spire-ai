## Context

The baseline-floor readiness audit is archived with verdict
`diagnostic_smoke_required`. Current is the only eligible non-teacher candidate,
its four frozen snapshot rows pass, and its API v2 and two API v3 own-trajectory
successors all stopped before one complete row. The known The Cleric, Scrap
Ooze, remove-sentinel, and sold-inventory boundaries are repaired. Courier
restock remains intentionally unsupported and is now reported by the exact
reason `unsupported_shop_courier_restock_semantics`.

The latest ignored successor module still exists at the hash and size bound by
the shop-support closeout. The diagnostic must exercise that exact module and
Current bridge without spending an untouched seed, updating any historical
result, or turning reused development trajectories into policy-quality data.

## Goals / Non-Goals

**Goals:**

- Establish whether the repaired Current bridge can complete at least one
  deterministic native own-trajectory row.
- Exercise four pre-existing development boundaries with a fixed, small,
  reviewable seed list.
- Preserve exact deterministic support-blocker rows instead of dropping them or
  treating them as terminal outcomes.
- Publish a canonical result that can be verified without native loading.
- Hand a structural result back to the baseline-floor readiness lane.

**Non-Goals:**

- Select or inspect a fresh seed, retry a formal cohort, or repair and rerun the
  diagnostic under one registration.
- Estimate Current quality, victory rate, reward, advantage, OPE, or a baseline
  floor.
- Change Current, bridge semantics, adapter behavior, simulator sources,
  Communication Mod, or live gameplay.
- Fit, load, qualify, promote, or train a model.

## Decisions

### Freeze four evidence-selected reused seeds

The registration fixes the ordered seed list `[7000, 7100, 2000, 10]`, two
fresh replays per seed, 500 decisions per replay, and a 600-second whole-run
deadline. No CLI option can change the seeds, order, replay count, or limits.

The choices are not trajectory screening: `7000` and `7100` are the first seeds
of the two consumed API v3 cohorts; `2000` is the first consumed legacy Current
bridge Stage 2 seed; and `10` is the reused development seed that reached the
Courier envelope in the support regression. All were consumed before this
proposal. The registration binds the predecessor journals, failures, repairs,
and baseline-readiness handoff that establish those roles.

Alternative considered: use one untouched seed or search consumed seeds for
good category coverage. Rejected because either would create new evidence or
select on observed trajectories before preregistration.

### Add a compact diagnostic runner without widening historical schemas

Add `analysis_scripts/noncombat_current_bridge_diagnostic_smoke.py` and focused
tests. Reuse stable canonical JSON, provenance, Current session, native wrapper,
and event diagnostic helpers from the reachable compatibility runner, but keep
new registration, result, journal, and artifact schema versions. Historical
evaluators and evidence remain byte-identical.

The diagnostic replay loop records the same action legality, input hashes,
event mapping, source nonmutation, fallback, tracker, terminal floor, and
outcome fields as the predecessor. It adds a row disposition so an exact
declared support blocker can preserve the last supported coordinates and action
prefix.

Alternative considered: teach the historical compatibility evaluator to accept
unsupported episodes. Rejected because that would change the meaning of two
already consumed formal structural studies.

### Treat only one exact Courier error as a declared support row

A replay may become `declared_support_blocked` only when native snapshot or
candidate generation fails with the exact underlying message
`unsupported_shop_courier_restock_semantics`. The row records seed, reason,
last supported floor and decision, prefix decisions and hashes, category counts,
and no terminal outcome. Both replays must match byte-for-byte after excluding
only replay index.

A matched declared blocker does not abort the fixed list. Any other native,
bridge, identity, legality, mutation, fallback, tracker, determinism, limit, or
timeout failure stops immediately and preserves completed prior rows. A support
row is never converted to victory, loss, or a complete terminal row.

Alternative considered: stop the whole smoke on Courier. Rejected because the
known support envelope is part of the diagnostic contract and dropping the
remaining fixed seeds would not answer whether another Current trajectory can
complete.

### Use three terminal verdicts with strict precedence

After valid identity and complete fixed-seed execution:

1. `current_bridge_diagnostic_failed` for any unexpected structural failure,
   nondeterminism, missing row, or missing aggregate category;
2. `current_bridge_diagnostic_support_limited` when all four rows are valid but
   none is terminal; or
3. `current_bridge_diagnostic_passed` when every seed has a deterministic
   terminal or declared-support row, at least one row is terminal, and route,
   shop, event, and card-reward counts are all nonzero across retained prefixes.

A pass establishes only a completed Current own-trajectory structural row. It
permits a new read-only readiness audit; it does not fill any of the eight
baseline-floor contract checks or change the outcome-support blocker.

### Separate implementation, identity registration, and one-shot execution

First commit and push the runner and fake-environment regressions. Then load
only the exact existing successor module's API/build identity, without creating
an `Environment`, and write a registration that binds module bytes, all physical
sources and contracts, runtime, metadata, implementation commit, fixed seeds,
limits, predecessors, output names, and all-false authority. Commit and push it.

Execution requires a tracked-clean tree, exact registration blob at `HEAD`,
`HEAD == origin/master`, matching native/source identity, and an absent output
directory. It atomically writes a started journal before the first environment.
The registration can execute once; interruption or partial failure leaves a
durable terminal diagnostic attempt and cannot be repaired or retried.

### Verify canonical artifacts without native code

Handled results publish configuration, execution journal, retained rows,
metrics, Markdown report, and manifest. A separate verify command checks exact
registration and predecessor bindings and recomputes every deterministic byte
without importing the native module or constructing an environment.

## Risks / Trade-offs

- [The fixed seeds miss a terminal row] -> Publish
  `current_bridge_diagnostic_support_limited` or a structural failure and stop;
  do not search or spend a fresh cohort.
- [A native call hangs inside C++] -> The started journal preserves the attempt;
  the external command bound may terminate it, and the same registration is not
  rerun.
- [Courier appears differently across replays] -> Classify nondeterminism and
  fail instead of averaging or retaining one replay.
- [Private predecessor helpers drift] -> Bind and regression-test exact source
  identity; fail registration verification on any byte change.
- [A pass is overinterpreted] -> Keep all downstream authority false and require
  a separate readiness audit before baseline-floor planning.

## Migration Plan

1. Strict-validate, commit, and push all planning artifacts.
2. Add red fake-environment tests, then implement the compact registration,
   diagnostic runner, canonical publication, and no-native verifier.
3. Run focused tests, compile checks, diff review, and the partitioned commit
   gate; commit and push the implementation.
4. Collect identity from the exact existing successor module without creating
   an environment, generate the registration, independently review it, then
   commit and push the preregistration boundary.
5. Recheck pushed state and execute exactly once. Preserve pass,
   support-limited, failure, timeout, interruption, or partial evidence.
6. Verify without native loading, publish closeout, refresh readiness, sync and
   archive the change, then commit and push.

Rollback before journal creation removes only the new unexecuted diagnostic.
After journal creation, rollback preserves all registration and execution
evidence and never reuses the same diagnostic identity.

## Open Questions

None. Seeds, order, replay count, limits, support reason, verdict precedence,
success metric, publication, and authority are fixed before implementation.
