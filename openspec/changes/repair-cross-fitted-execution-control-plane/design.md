## Context

The consumed cross-fitted successor produced a structurally valid post-start
failure after 12 debits and 11 completed accesses, with no complete chunk. Its
63,171,200-byte registration contains 275,853 provenance rows. A source-only
microbenchmark parsed that file in 0.530 seconds but spent 56.016 seconds in one
`_registration_for_identity` call because the helper validates the registration
and `registration_sha256` validates it again.

Static call-graph reconstruction gives a lower bound of 20 identity-helper
entries per completed access, excluding extra registration hashing in journal
header reconstruction. Producer closeout then took about 2,228 seconds from
failure witness to manifest. The terminal ledger remained at
`charged_seconds=0.0` because elapsed time is committed only at a complete
checkpoint or infrastructure interruption. These are control-plane defects;
the run retained no mechanism evidence from which to change the estimator,
reward, ranker, or cohort.

## Goals / Non-Goals

**Goals:**

- Make complete registration validation and canonical hashing constant per
  process boundary rather than proportional to seed count or helper nesting.
- Preserve exact journal, schedule, resource, lease, checkpoint, artifact, and
  independent-verification semantics.
- Persist elapsed charge before every post-start terminal intent, including a
  first-chunk non-infrastructure failure.
- Remove redundant producer-only intent and registration reopening while
  preserving full recovery validation in a later process.
- Make true Python child liveness, not wrapper status, the explicit output-root
  inspection boundary.
- Prove the repair with source-only structural and lifecycle regressions before
  any new source identity or registration is considered.

**Non-Goals:**

- Mutating, resuming, retrying, or re-verifying the consumed terminal under a
  changed source identity.
- Loading the native simulator, importing Torch in control tests, accessing a
  seed, fitting a baseline, updating a model, or running an empirical cohort.
- Changing the ranker, state features, folds, ridge estimator, objective,
  reward, optimizer, saturation threshold, schedule, or artifact schemas.
- Optimizing pytest globally, redesigning all experiment runners, or adding a
  generic cache framework.
- Establishing policy quality, causal effect, target-supported outcome, formal
  RL readiness, gameplay value, qualification, or promotion.

## Decisions

### Introduce one private validated execution context

Add a private context type owned by the cross-fitted control plane. Its factory
accepts raw registration, identity, and output path; performs complete
validation once; computes the canonical digest directly from the validated
mapping without calling the validating public digest helper again; verifies the
logical identity and registered output; and stores an independently owned
normalized registration plus its digest, normalized identity, and resolved
output.

The context remains a private mapping-compatible object so existing control
helpers can index registration fields. `_registration_for_identity`,
`_registration_for_output`, `registration_sha256`, and internal validation
entrypoints recognize this exact private type and return its bound values
without full revalidation. Raw mappings continue through the existing complete
boundary validation. The factory deep-copies through current validation, so
mutating the caller's original mapping cannot alter the context.

The authorized execution creates the context only after request, approval,
authorization, pushed-source, native provenance, and isolation inputs validate
but before native loading and journal operations. It passes the context through
all nested helpers. No global cache, object-id cache, weak-reference cache, or
cross-process cache is used.

Alternative: memoize by `id(registration)`. Rejected because object reuse and
mutation make identity caching unsafe and non-auditable. Alternative: skip
validation inside journal functions unconditionally. Rejected because direct
source-only callers and recovery still need a complete boundary.

### Generalize attempt charging before terminalization

Replace the infrastructure-only elapsed-charge helper with one bounded attempt
charge operation. It observes the current clock, adds current attempt elapsed
to the durable origin, reconciles debited accesses, appends a monotonic resource
revision with an explicit reason, and clamps only at the registered time limit.

The execution exception handler closes any pending access, then charges the
attempt before deciding whether the exception is resumable or terminal. A
non-infrastructure failure now charges before its failure witness and
post-isolation observation. Completion and saturation also charge immediately
before post-isolation and terminal intent. If an existing ledger already
contains the same final coordinate, the operation is idempotent.

The verifier requires the final charge reason/coordinate for terminal bundles
produced by the repaired source identity and reconstructs exact synthetic clock
fixtures. Source tests cover zero prior charge, nonzero resume origin, deadline
clamping, and a failure before checkpoint zero.

Alternative: infer elapsed time from filesystem timestamps. Rejected because
timestamps are noncanonical and not independently bound. Alternative: update
charged seconds before every seed. Rejected because it adds durable writes and
does not fix terminal omission; one final attempt event is sufficient.

### Carry terminal intent forward in the live producer

`publish_terminal_intent` returns the immutable canonical intent it writes.
The same-process closeout passes that intent to terminal construction rather
than calling `load_terminal_intent`, which is reserved for recovery and
independent reopening. Terminal construction still reloads the small journal,
resource ledger, and checkpoint chain and compares them to the intent. It builds
the final inventory after terminal publication, as required by phase-specific
artifact membership.

All helpers receive the validated context, so any necessary state replay does
not trigger complete registration validation. Recovery from an existing intent
or terminal starts from raw files, creates one fresh validated context, and
performs all current byte and inventory comparisons before publishing missing
bytes.

Alternative: reuse the prefix inventory as the final inventory. Rejected
because terminal and intent change managed membership. Alternative: weaken the
independent verifier to trust the producer context. Rejected; the verifier stays
standard-library, source-isolated, and complete.

### Keep liveness supervision explicit and fail closed

The repository direction and execution procedure identify the actual Python
child PID/process handle before waiting. A wrapper timeout is recorded only as a
monitoring event; it cannot release the output-root inspection gate. If the
child remains alive or liveness is ambiguous, no output file is read. After the
child is absent, the lease must be readable before verifier invocation.

The control plane and verifier retain their exclusive lease behavior. Focused
tests preserve live-owner rejection, dead-owner recovery, and unreadable-lease
fail-closed behavior. This change does not implement a broad Windows service or
job-object framework.

### Use structural performance regressions

Tests patch the complete registration validator with a counter, create one
validated context, and drive synthetic 64-access plus terminal-failure flows.
The counter must not increase with seed count or helper nesting. Separate
fixtures mutate raw registration, schedule, identity, journal bytes, resource
hash chains, and managed inventory to prove the fast path does not weaken
boundaries.

A small source-only timing smoke may compare raw parsing and context reuse, but
wall-clock thresholds are descriptive because CI and Windows storage vary.
Correctness gates use call counts and byte identities rather than brittle time
limits. Torch/native import-isolation probes remain mandatory.

## Risks / Trade-offs

- [A trusted context could hide accidental in-process mutation] -> Keep the type
  private, own the validated copy, expose no mutation API, and test caller-input
  mutation plus durable byte identities.
- [Fast-path helpers could bypass corruption checks] -> Skip only complete
  registration work; retain journal replay, schedule, hash-chain, lease,
  resource, checkpoint, and inventory validation and add negative regressions.
- [Changing charge ordering could affect recovery coordinates] -> Append one
  explicit monotonic event before intent and test pre-checkpoint, checkpoint,
  resume, saturation, and interruption boundaries.
- [Same-process intent reuse could diverge from recovery] -> Compare the
  in-memory intent to the bytes just written and keep the existing full loader
  for every later process.
- [The consumed terminal cannot be verified after source bytes change] -> Keep
  its already verified bundle and postmortem immutable; tests use synthetic
  fixtures, and any future execution receives a new source identity.

## Migration Plan

1. Add RED context call-count, mutation, charge, terminal reuse, recovery, and
   liveness regressions without native loading.
2. Implement the private context and pass it through only the cross-fitted
   producer path.
3. Generalize attempt charging and update the independent verifier and
   synthetic terminal fixtures.
4. Rework same-process closeout to pass its intent forward while preserving the
   raw-file recovery path.
5. Run import isolation, focused control/verifier tests, strict OpenSpec, an
   independent review, and the repository commit gate once at the source
   boundary.
6. Update project direction, commit, and push source only. Do not create a
   registration or execution request in this change.

Rollback before publication removes the additive context and restores the
previous helper calls/tests. Rollback after publication reverts the source
commit. In both cases the consumed terminal directory, reports, and seeds stay
unchanged.

## Open Questions

None. The audit fixes the repair boundary; empirical throughput and mechanism
quality remain separate future decisions.
