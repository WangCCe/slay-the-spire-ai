## Context

The consumed v1 registration bound implementation `18edd1400`, the preserved
train dataset, and `sts_lightspeed` source, then ran exactly once. The command
failed after 293.7 total seconds because the timed audit body exceeded its
fixed 120-second limit. Publication occurs only after that check, so the output
root remained absent and no substantive verdict exists.

Static inspection identifies redundant exact work without needing another
corpus execution. The CLI loads and validates the gzip once inside identity
validation, discards that object, loads it again, and then the timed body deep
copies and canonicalizes the full in-memory dataset a third time. Each adapter
candidate also reserializes a policy view whose exact SHA-256 is already stored
and validated in the corpus. Structured features rebuild identical global
state features for every candidate in one decision.

The recovery must optimize those operations without changing any value that can
reach a canonical signature, metric, source fact, suitability check, verdict,
or authority field. The failed registration is consumed and cannot be retried.

## Goals / Non-Goals

**Goals:**

- Pass one explicitly validated in-memory train object from identity loading to
  the audit body, with exactly one gzip decode per run/validate command.
- Reuse only hashes whose payload equality was already checked by the corpus
  validator, and cache only pure per-decision feature components.
- Prove optimized candidate/decision signatures and aggregate metrics equal the
  v1 reference implementation byte-for-byte on adversarial synthetic fixtures.
- Demonstrate bounded runtime on a generated 602-row non-corpus workload before
  creating a fresh registration.
- Bind the v1 blocked failure and execute one fresh registered recovery under
  the same 120-second audit-body limit.

**Non-Goals:**

- No retry or edit of the v1 registration, no increase or reinterpretation of
  its time limit, and no reconstruction of its discarded result.
- No change to corpus rows, categories, signature ids/dimensions, leakage
  fields, semantic action keys, dependency statuses, suitability checks,
  verdict order, report schemas, or authority.
- No real-corpus profiling or dry run before fresh registration; no native
  build/load/call, model fitting, simulator seed, gameplay, reward/outcome
  analysis, formal RL, qualification, or promotion.

## Decisions

### 1. Introduce a validated execution context

A `ValidatedAuditContext` will contain the validated registration, train input,
identity summary, and source facts. One loader performs all physical binding,
runtime, gzip/manifest, dataset, lineage, and source checks and returns that
context. `run` and strict `validate` each call it exactly once.

The timed audit function accepts only this context and does not call
`validate_train_input`, deep-copy the dataset, recompute its canonical SHA, or
touch disk. Public fixture helpers may still validate untrusted synthetic input
outside the timed path. A call-count regression will fail if the archive loader
or full dataset validator is re-entered after context construction.

Moving already completed identity validation outside the audit timer does not
weaken the 120-second contract: the timer continues to cover all source-policy
reconstruction, four representations, alias metrics, suitability checks,
verdict construction, and canonical artifact building. Total command time is
reported separately in the noncanonical journal.

### 2. Reuse validated adapter policy-view hashes

The corpus validator already recomputes every
`project_policy_view(state, candidate)` and compares both payload and stored
SHA-256. The optimized representation path will therefore consume the stored
hash in the validated row. Missing, reordered, duplicated, or unvalidated
entries block before timing.

The v1 serializer remains as a reference-only fixture helper. Tests compare its
candidate hashes and decision hash with the optimized path on leakage fields,
collection order, duplicate cards, route maps, and malformed policy-view rows.
Using snapshot hashes or trusting unvalidated rows was rejected because neither
proves the candidate-specific leakage projection.

### 3. Cache structured global features once per decision

The optimized path will call the existing structured feature primitives. It
computes `_global_features(state, category)` once, copies that exact sorted
mapping per candidate, adds `candidate.kind`, and then invokes the unchanged
route or card category helper. It keeps the same 2,048-dimensional signed hash,
normalization, float32 dtype, candidate order, and byte hashing.

Reference-versus-optimized tests compare both the full semantic feature maps
and final contiguous float32 bytes. No memoization crosses decision rows, and
no approximate numeric cache is allowed. More invasive graph algorithms or a
new feature schema were rejected because they expand the equivalence surface.

### 4. Preserve canonical logic and bind recovery lineage

Registration schema v2 adds only the v1 failure-record binding and the fixed
recovery contract (`single-validated-load-v1`, trusted validated policy-view
hashes, per-decision structured globals). It retains the same input corpus,
external source files, signature definitions, suitability checks, verdict
order, row/candidate/model/native limits, and 120-second audit-body limit.

All report/manifest schemas and canonical computation functions remain the
same. The v2 registration/configuration bytes naturally differ, but for a given
synthetic logical row the source reconstruction, signature hashes, metrics,
suitability, verdict, and report content must match the v1 reference.

### 5. Gate fresh registration on synthetic proof only

Before implementation commit, a generated workload will contain exactly 300
route and 302 card-reward multi-candidate rows, matching the registered
multi-choice category counts but using deterministic synthetic states/actions
and no registered seed or source snapshot. The optimized representation pass
must complete within 90 seconds on production Windows Python. A smaller
adversarial fixture must match v1 reference bytes exactly.

The synthetic gate is a regression/performance check, not evidence. After it,
focused tests, compilation, strict OpenSpec validation, and the repository
commit gate must pass. Only then may implementation be committed, one fresh v2
registration be committed and pushed, and one canonical recovery run occur.
The real run must still finish its timed body within 120 seconds; a miss is a
terminal blocked result with no retry.

## Risks / Trade-offs

- **Stored hashes could hide payload drift** -> The single context loader keeps
  the existing payload-and-hash validation and tests prove one invocation.
- **Private structured helpers could drift** -> Bind their source file and test
  full feature-map plus vector-byte equivalence, failing closed on import or
  key differences.
- **Synthetic repeated maps understate real topology cost** -> Require a
  90-second synthetic ceiling for headroom and retain the decisive 120-second
  fresh-run gate.
- **Timing can vary with host load** -> Use production Python, no parallel test
  process, report elapsed time, and do not retry a registered miss.
- **Schema v2 no longer loads v1 registrations** -> Preserve v1 bytes and
  failure record as historical evidence; only the fresh recovery registration
  is executable by the new runner.

## Migration Plan

1. Add v1-reference/optimized helpers, validated context, and synthetic
   equivalence/load-count/performance regressions without reading the train
   gzip.
2. Run focused and adjacent tests, compilation, strict OpenSpec validation, the
   synthetic 602-row gate, and one repository commit gate.
3. Commit/push implementation and recovery OpenSpec, then create, verify,
   commit, and push one v2 registration binding the v1 failure.
4. Execute once, strictly recompute if published, record either the substantive
   verdict or terminal failure, and update project direction.
5. Sync/archive both changes only if recovery publishes and validates the
   originally required canonical result; otherwise retain their blocked state.

Rollback restores the v1 audit implementation and removes only v2 recovery
code/tests/registration/results. It never alters the consumed registration,
failure record, source checkout, train corpus, live config, or checkpoints.

## Open Questions

None. Optimizations, equivalence boundary, synthetic workload, time limits,
lineage, and one-shot execution are fixed before implementation.
