## Context

The successor collector samples only states where the frozen r16 parent chooses
end turn and the deployment guard replaces it with a legal energy-spending
action. Its current support target is all 7,685 r14/r15 replay transitions,
which also includes ordinary card actions and end turns the guard does not
replace.

A read-only audit joined four sealed no-takeover shadow sessions to their raw
decision states. Across 20 runs and 768 guard-replacement opportunities, the
merged fresh successor corpus passes all unchanged support gates: coverage
`0.940104`, ESS `872.930`, maximum weight `0.009695`, floor-23-27 coverage
`1.0`, floor-28-34 coverage `0.757143`, and all weighted SMDs below their
limits. The same corpus fails against all replay transitions. Those 20 runs
informed this design and cannot be reused as formal confirmation.

## Goals / Non-Goals

**Goals:**

- Materialize the real deployment-opportunity population with immutable row,
  run, session, parent, trace, and decision-state provenance.
- Confirm the target definition on 20 new parent-only runs before changing the
  successor support decision.
- Reuse the existing cell definition and every numerical support threshold.
- Run the fixed paired control/successor fit once when, and only when, aligned
  support passes.
- Keep implementation and verification to one cohesive source boundary and
  one full commit gate.

**Non-Goals:**

- Giving a candidate live action authority during target collection.
- Changing r16, simulator mechanics, corpus labels, context bins, thresholds,
  optimizer settings, update count, calibration rule, or offline policy gates.
- Online learning, hyperparameter search, repeated holdout collection, matched
  live candidate evaluation, qualification, promotion, or production writes.

## Decisions

### Define the target by deployed guard replacement

A real target row is a combat decision where the exact production parent
selects RL action 90, the deployed guard emits a different legal action, and
the executed action equals that guard action. Candidate score, intervention,
or candidate-support fields do not define membership.

Alternative: keep all replay transitions. Rejected because that population
contains states outside the model's action-relative deployment surface and the
20-run audit demonstrates a material support-decision reversal.

Alternative: select replay rows by their final action. Rejected because the
r14/r15 replay schema does not retain raw parent or guard telemetry and cannot
distinguish ordinary card choices from replaced end turns.

### Reuse no-takeover shadow instrumentation

The collection wrapper will reuse the action-relative live-shadow hook to
record raw parent, guard, executed action, parent parameter hash, and state
identity while enforcing `candidate_has_authority=false`. Target extraction
ignores every candidate output. Each telemetry row joins uniquely to the
nearest in-combat raw decision-state row with identical floor and turn within
100 ms.

Alternative: add a second gameplay action path. Rejected because it would risk
changing production action selection merely to collect context.

### Use a new 20-run holdout in fixed batches

Formal confirmation consists of four separately identified five-run batches.
The target requires 20 completed AI run records, unique run seeds absent from
the 20 development runs, at least 300 joined opportunities, at least 20
opportunities on floors 23 through 34, no duplicate joins, and exact r16 parent
and no-takeover evidence. An interrupted batch may resume only to reach its
registered five completed runs without changing configuration or counting a
run twice.

Alternative: reuse the development runs. Rejected because they selected the
target definition. Alternative: collect until the support gate passes.
Rejected because outcome-dependent stopping would bias the target.

### Publish context rows rather than a replay checkpoint

The target artifact stores run/session identity, trace decision identity,
floor and canonical floor stratum, HP ratio, occupied potion and relic counts,
HP quartile, and context-cell ID. The support adapter derives simulator weights
from these rows directly. It does not synthesize actions, rewards, next states,
or a fake replay buffer.

Alternative: encode minimal tensors as a replay checkpoint. Rejected because
that would imply transition semantics the target does not contain.

### Fit in the same change after a hard boundary

The runner validates the target and merged corpus identities, evaluates the
unchanged support gate, and constructs no optimizer if any condition fails. On
a pass, it invokes the existing frozen-parent paired fit with identical rows,
weights, arm seeds, 4,096 updates, calibration rule, deferred fresh-label
access, and hard/descriptive decisions. The new registration binds the merged
corpus hashes and target hash.

Alternative: make target confirmation and fit separate changes. Rejected
because the fit recipe already exists and another planning cycle would add no
scientific independence after the holdout and support gate are sealed.

## Risks / Trade-offs

- [Twenty runs may still undersample late opportunities] -> Require a fixed
  minimum late-row count and close rather than extending the cohort.
- [Rows within one run are correlated] -> Bind 20 run identities across four
  batches and report per-batch metrics descriptively alongside the aggregate
  hard gate.
- [Timestamp joining could select the wrong raw state] -> Require identical
  floor and turn, unique nearest matches within 100 ms, monotonic event order,
  and exact executed-action consistency where the raw action is encodable.
- [Shadow candidate evaluation could affect latency] -> Keep takeover disabled,
  exclude candidate fields from membership, retain latency/error evidence, and
  fail any batch with candidate authority or runtime errors.
- [Changing the target after seeing old data could overfit the definition] ->
  Freeze this exact definition before launching any of the 20 formal runs and
  evaluate the new target only once.
- [A passing aligned gate does not prove policy quality] -> Keep the existing
  paired fresh policy gates unchanged and grant no live or production authority.

## Migration Plan

1. Implement target extraction, validation, support adaptation, and conditional
   paired-fit delegation with fixtures.
2. Run focused tests and one full commit gate, then commit and push source plus
   four batch registrations before gameplay.
3. Collect exactly four five-run parent-only batches and atomically publish the
   fresh target.
4. Evaluate aligned support once; stop on failure or execute the fixed paired
   fit once on success.
5. Commit reports and artifacts, sync specs, and archive the change.

Rollback is additive: stop using the new target and artifacts. Existing replay,
successor corpora, production configuration, and r16 checkpoint remain
unchanged.

## Open Questions

None. Exact source and artifact hashes are resolved after implementation is
committed and before the first live batch starts.
