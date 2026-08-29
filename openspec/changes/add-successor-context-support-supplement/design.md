## Context

The consumed r2 action-relative first-successor corpus contains 5,493 fit,
1,849 calibration, and 1,896 fresh source states. It closed before optimizer
construction because the merged train view had ESS `691.368` and the fresh view
had coverage `0.803383`, ESS `243.204`, floor-23-27 coverage `0.628176`, and
floor-28-34 coverage `0.429569`.

A read-only context opportunity audit reused historical, seed-disjoint combat
corpora without loading a native module or fitting a model. Uniformly adding
battle 10 could reach only `0.881197` real mass. Battle 3 plus battle 10 reached
`0.919844`; across five deterministic subset projections, 1,024 battle-3 and
1,536 battle-10 fresh profiles kept coverage at or above `0.915940`, ESS at or
above `662.690`, and maximum normalized weight at or below `0.008477`. Adding
384 battle-3 train profiles kept projected train ESS at or above `813.567`.

The existing r2 artifacts are immutable and its execution identity cannot be
reused. This design therefore adds a separate supplemental collector and uses
the same Windows CPU LightSTS adapter and frozen simulator-only r16 parent.

## Goals / Non-Goals

**Goals:**

- Collect only the context profiles indicated by the opportunity audit.
- Preserve complete first-successor pair labels and the exact r2 corpus schema.
- Merge the supplement with r2 deterministically while retaining row and seed
  provenance.
- Reapply the unchanged real-context support and integrity gates before any
  optimizer exists.
- Publish a reusable merged corpus when support passes and a bounded diagnostic
  report when it does not.

**Non-Goals:**

- Fitting either ablation arm, changing thresholds, or evaluating a policy.
- Starting Slay the Spire or CommunicationMod.
- Loading or writing a production checkpoint.
- Changing native simulator mechanics, the r16 shadow parent, r14/r15 replay,
  context bins, support gates, labels, or continuation returns.
- Treating historical proxy projections as policy-quality or live evidence.

## Decisions

### Add a wrapper instead of changing the consumed r2 runner

A new `combat_rl_action_relative_successor_context_supplement.py` module will
import the r2 collector and validation helpers. The consumed module and r2
artifacts stay byte-for-byte unchanged. This also makes rollback equivalent to
discarding the new registration and output.

Alternative: parameterize the existing runner. Rejected because changing a
consumed execution path would weaken historical replayability and broaden the
regression surface.

### Use partition-specific battle slices

The formal registration will bind these collision-checked cohorts:

- train supplement: seeds `283000..283383`, battle index `3`;
- fresh battle-3 supplement: seeds `284000..285023`, battle index `3`;
- fresh battle-10 supplement: seeds `286000..287535`, battle index `10`.

All slices preserve r2's ascension, source-state retention, source-decision,
canonical-action, continuation, discount, advantage-margin, wall-time, and
storage settings. A tiny separately identified smoke uses only dedicated smoke
seeds and grants no formal evidence.

Alternative: repeat all five battle indices with the same partition ratios.
Rejected because the read-only audit shows battle 0 adds no context support and
battles 6 and 9 do not replace the missing battle-3 cells.

### Merge complete successor corpora, not context tensors alone

The runner will offset pair `source_rows` while concatenating r2 and supplement
source tensors, metadata, and pair tensors. It will preserve r2 calibration
unchanged, merge the train supplement into fit, and merge both fresh slices into
fresh. Every merged corpus must pass the existing successor-corpus validator,
round-trip identity check, and exact partition/seed inventory checks.

Alternative: publish only context rows. Rejected because a support pass would
then require another native collection before the existing paired fit could use
the evidence.

### Keep retry behavior practical and identity-scoped

Source-only validation may be corrected before a started receipt exists. Once
an execution starts, its ID and output path are never overwritten; an
infrastructure or implementation failure is reported and any corrected run uses
a new registration identity with explicit predecessor binding. The cohort and
scientific gates cannot be silently changed inside a retry.

This avoids both blind retries and the earlier overly rigid rule that made a
recoverable pre-start tooling error permanently consume the scientific plan.

### Stop at merged support

The collector computes support from the merged fit plus unchanged calibration
and merged fresh corpus. A pass grants only eligibility for a separate weighted
fit change; a failure closes this supplement without fitting or tuning.

## Risks / Trade-offs

- [Historical context projections may overestimate new-seed coverage] -> Use
  the higher-margin 1,024 plus 1,536 fresh profile point and retain the unchanged
  hard support gate.
- [Battle-3 collection may still miss rare real cells] -> Preserve exact
  missing-cell and concentration diagnostics; do not substitute another battle
  or widen the cohort after execution begins.
- [Merged pair indices may be corrupted] -> Test offset behavior, validate every
  merged corpus, and compare serialize/load identities before publication.
- [The native run is still costly] -> Run a deterministic two-slice smoke first,
  then execute one bounded formal collection; do not run the full pytest gate
  more than once for the cohesive implementation boundary.
- [Seed values may already be bound by an overlooked successor registration] ->
  preflight scans the action-relative successor lineage's tracked and published
  registrations plus r2 row metadata and fails before native loading on any
  collision. Unrelated combat experiments and numeric metric values are not
  treated as this corpus's seed ledger.

## Migration Plan

1. Implement merge, cohort validation, registration, preflight, and report
   rendering with focused fixtures.
2. Run the dedicated smoke and verify deterministic identities without fitting.
3. Commit and push the source plus formal registration after all source-only
   checks pass.
4. Run one bounded formal native collection under the registered Windows
   interpreter.
5. If merged support passes, preserve the artifacts for a separate fit change;
   otherwise publish the failed support decision and stop.

Rollback requires no migration: remove or ignore the new unconsumed
registration before start, or retain a started failure report while leaving r2
and all production paths untouched.

## Open Questions

None. Exact input hashes and the final collision inventory are resolved by the
source-only registration step after implementation is committed.
