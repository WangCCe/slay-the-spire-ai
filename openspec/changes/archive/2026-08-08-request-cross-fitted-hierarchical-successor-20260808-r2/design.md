## Context

Registration evidence commit `7b3221c7b099eda2853bfc405c4a67f5b5a8123a`
contains the exact compact v2 registration, and closeout commit
`b0237cc8f266939bf72cf1395fd72c9971ef9f61` syncs and archives its
contract. The registration binds the r5 readiness source and publication, the
complete fresh schedule, external identities, immutable resource limits, and an
all-false authority map. No request, approval, or authorization exists.

The existing source-only `render-request` CLI first replays immutable readiness
verification for compact v2 and then calls the pure deterministic request
builder. The request carries desired operations and the exact execution-
authority shape, but it has no effect until a separately published exact
approval and tracked authorization pass source-only preflight.

## Goals / Non-Goals

**Goals:**

- Publish one canonical execution-request v1 derived byte-for-byte from the
  pushed 20260808-r2 registration.
- Preserve exact registration, native, runtime, source, output, schedule,
  resource, and resume terms with no new choice or tuning surface.
- Independently verify request structure and digest after the producer has
  replayed readiness evidence.
- Keep approval, authorization, native loading, seed access, fitting, training,
  and all empirical work at later boundaries.

**Non-Goals:**

- Building or resolving a standing delegation, approval, or authorization.
- Loading native/Torch/model code, creating the registered output root,
  accessing an environment or seed, fitting, training, evaluation, gameplay,
  CommunicationMod, qualification, promotion, or policy-quality claims.
- Changing any registered term or implementation byte.

## Decisions

### Render through the source-only CLI

Invoke the tracked
`analysis_scripts.noncombat_cross_fitted_hierarchical_learning_experiment`
module through a Windows Python `-I -c` bootstrap that adds only the exact repo
root to `sys.path` and dispatches `main()` with `render-request`, the repository
root, and the exact pushed registration path. Capture canonical stdout into an
additive staging file only after exit 0. This preserves isolated mode while
making the repo-local package import explicit; the entry point revalidates the
compact readiness publication before deriving the request.

Alternative: call `build_exact_execution_request` directly. Rejected for
publication because the pure helper intentionally assumes an already validated
in-memory context and does not itself replay external readiness evidence.
Alternative: execute the file path directly under `-I`. Rejected because
isolated mode removes the repo root and the file cannot import its bound sibling
package when readiness decoding begins.

### Keep requested authority distinct from granted authority

The request's `authority` remains the registration's all-false map.
`requested_execution_authority` is the exact deterministic map with true only
for environment construction, execution, model fitting, native loading, seed
access, and training. `operations` describes the fixed cross-fitted baseline
fit and bounded optimizer work. These fields express the later authorization
candidate; they do not grant it.

Alternative: keep every request field false. Rejected because an inert request
would not specify the operation a later approval and authorization bind.

### Publish request and review only

The request path is
`reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_execution_request.json`.
The deterministic review binds the request's file and canonical digests, the
registration file/digest/commit, exact operations/resources/resume/output, the
producer readiness replay, independent request validation, blocked-import
delta, output-root absence, and absence of approval/authorization artifacts.

Alternative: resolve the standing delegation in the same change. Rejected
because approval must bind a stable pushed request digest and remain separately
reviewable and revocable before publication.

### Reuse evidence-only verification scope

Run focused request/control/verifier tests, canonical/self-digest probes,
source-only import checks, strict OpenSpec, and bounded independent review. Do
not rerun the long commit gate or gameplay because this change edits no
implementation or test source and changes no live behavior.

## Risks / Trade-offs

- **Registration or readiness bytes drift before rendering** -> CLI replay fails
  before emitting a request; do not substitute a nearby artifact.
- **Requested authority is mistaken for granted authority** -> Review records
  all missing approval/authorization artifacts and states that execution remains
  blocked.
- **Request bytes are changed after approval** -> Every later approval and
  authorization binds the exact request digest; a different request requires a
  new identity and review.
- **stdout capture produces noncanonical bytes** -> Parse, deterministically
  rerender, compare byte-for-byte, and publish only on equality.

## Migration Plan

1. Validate, commit, and push this OpenSpec plan.
2. Confirm exact pushed registration bytes, source ancestry, registered-output
   absence, and downstream-artifact absence.
3. Invoke `render-request` once for publication, capture stdout in staging, and
   require canonical round-trip equality.
4. Independently validate the exact request against the registration, publish a
   deterministic review, and run focused verification.
5. Commit and push request evidence while the change remains active.
6. Sync the request requirement, update project direction, archive the change,
   and commit and push closeout separately.
7. Stop. A later change may inspect the current user delegation/revocation state
   and resolve one exact delegated approval and authorization candidate.

Before step 5, rollback deletes only additive untracked request artifacts. After
push, preserve the request and create a new identity for any correction.

## Open Questions

None.
