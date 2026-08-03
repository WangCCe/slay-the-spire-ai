## Context

The formal readiness r2 matrix passes state/action, reference isolation,
reward, and evaluation, but blocks baseline policy and outcome support. The
SimpleAgent imitation lane, structured ranker, and route/card residual model
are terminal valid negatives, and the teacher-suitability audit closes
SimpleAgent as policy-quality truth. Bottled remains auxiliary. Current is the
only remaining non-teacher policy already used in production gameplay.

The Current simulator bridge passes its four frozen Stage 1 rows, but its two
own-trajectory successors consumed fresh cohorts without completing one row:
first on missing reachable event semantics and then on shop remove sentinel
hydration. Those defects and later sold-inventory defects are repaired. Courier
restock remains intentionally unsupported, and impossible potion purchases are
filtered. These changes do not retroactively turn either consumed cohort into
positive compatibility evidence.

## Goals / Non-Goals

**Goals:**

- Recompute one exact planning verdict from immutable current evidence.
- Select or reject every plausible non-teacher baseline candidate by fixed
  rules rather than preference.
- Prevent unsupported episodes from disappearing through complete-case or
  survivor-only evaluation.
- Name the least expensive next prerequisite before any untouched seed is
  selected.
- Keep the implementation compact and deterministic.

**Non-Goals:**

- Load a native module, construct an environment, select seeds, or run a
  compatibility or baseline cohort.
- Fit, tune, compare, or promote a model.
- Change Current, Bottled, SimpleAgent, the adapter, bridge, reward, OPE, or
  gameplay configuration.
- Resolve the independent target-supported-outcome blocker.

## Decisions

### Bind only decision-bearing evidence

One registration will bind the formal readiness r2 report, policy-validity and
warm-start negatives, teacher-suitability result, Current bridge r2 result,
both consumed own-trajectory compatibility results, subsequent reachable/shop
repair closeouts, the current support-envelope closeout, formal reward result,
and outcome feasibility result. Each path, hash, size, and expected identity is
fixed before analysis.

A broad report-directory crawl was rejected because unrelated historical and
untracked files would make the audit unstable. Reinterpreting old negative
cohorts after repairs was rejected because their registered executions remain
consumed failures.

### Classify candidates by role before quality

The audit will classify:

- Current as the only eligible non-teacher baseline candidate, conditional on
  own-trajectory structural closure;
- SimpleAgent as an auxiliary deterministic control only;
- Bottled as an auxiliary label/diagnostic oracle only; and
- learned imitation, structured, residual, and seeded-initial policies as
  negative evidence or weak controls rather than credible baseline floors.

Agreement with a reference, training loss, or improvement over seeded
initialization cannot make a candidate eligible.

### Require conservative unsupported-episode accounting

Any future baseline-floor registration must include every selected episode in
its denominator. An exact declared support-envelope blocker may be recorded at
the last supported snapshot, but it must count as a non-victory and as the
registered conservative floor value for paired and aggregate lower-bound
metrics. Unsupported episodes may not be dropped, replaced, replayed with a
different seed, or hidden in a supported-only headline. The registration must
also fix an unsupported-rate ceiling before execution.

Requiring complete mechanics support was rejected as unnecessarily blocking a
conservative floor. Complete-case analysis was rejected because policy paths
can change exposure to Courier and would create survivor bias.

### Require a reused-seed structural smoke before fresh evidence

Current is not ready for a baseline-floor preregistration because no
own-trajectory Current cohort has completed a row under the repaired API v3
surface. The exact next prerequisite is a separate, bounded diagnostic change
using only already-consumed development seeds. It must bind the current module,
bridge, contracts, fixed seeds and limits, replay deterministically, classify
declared support blockers separately, and grant no quality or readiness
authority.

Only a clean diagnostic result may support a later proposal that fixes fresh
compatibility/evaluation cohorts, comparison controls, absolute and paired
quality thresholds, unsupported-rate ceiling, bootstrap contract, and final
holdout rules. Directly spending a third fresh compatibility cohort was
rejected because the new support envelope has not yet been exercised through
Current trajectories.

### Publish a small canonical result

The implementation will use one registration JSON, one compact Python
analyzer, one JSON result, one Markdown rendering, and focused tests. Strict
mode regenerates both outputs byte-for-byte. It will not introduce a generic
study framework or artifact-manifest hierarchy.

## Risks / Trade-offs

- [The audit adds another planning gate] -> It replaces a likely consumed
  fresh-cohort failure with a cheap reused-seed diagnostic and names one exact
  successor.
- [Counting unsupported episodes as failures understates Current quality] ->
  That is intentional for a credible lower bound; supported-only diagnostics
  may be shown separately but cannot drive the pass verdict.
- [Development seeds are not policy-quality evidence] -> The next smoke has
  structural-only authority and cannot satisfy the baseline floor.
- [Current can change after the audit] -> Every later registration must bind
  the exact Current source and semantic configuration; drift invalidates this
  handoff.
- [Outcome support remains blocked] -> The audit reports it independently and
  never treats a baseline pass as training readiness.

## Migration Plan

1. Commit and push all planning artifacts.
2. Add red tests for exact evidence, candidate roles, unsupported accounting,
   verdict precedence, and canonical rendering.
3. Implement the compact read-only audit and publish its current result.
4. Run focused pytest, the partitioned commit gate, and strict OpenSpec
   validation.
5. Sync, archive, and update project direction from the observed result.

Rollback removes only these new files and the direction update.

## Open Questions

No question blocks the planning audit. Numeric quality thresholds and fresh
cohort membership deliberately remain decisions for a later proposal after
the reused-seed structural smoke.
