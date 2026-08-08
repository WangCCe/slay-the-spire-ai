## Context

The r5 readiness source `ffd9acc444258483d172529eccfe8ccb05c9bb9b`
contains the current producer, runtime, independent verifier, seed helper, and
delegation implementation. Publication commit
`0c62aff2fb301dd491017bbf2e775c36a177bf67` contains the independently verified
`go`, candidate inventory, source-keyed receipts, and closeout. The readiness
identity grants only registration-proposal eligibility.

The existing compact v2 builder and producer/verifier validation paths are
already implemented and source-only. This change therefore creates evidence;
it does not change the algorithm or control plane. The registered output root
is a future simulator-only evidence root under `reports/`, not a live game or
CommunicationMod path.

The source-only CLI entry points `inspect-registration` and `render-request`
reverify immutable readiness evidence before returning. The lower-level
`build_exact_execution_request` helper intentionally remains a pure structural
derivation for already validated in-memory contexts; this change neither calls
it nor treats direct helper use as the source-only request-publication entry
point.

## Goals / Non-Goals

**Goals:**

- Publish one deterministic compact v2 registration for the 20260808-r2
  successor identity.
- Reobserve and bind source, native, runtime, CommunicationMod configuration,
  production checkpoints, output root, schedule, and every fixed limit without
  loading Torch or the native module.
- Validate the artifact through both producer and independent standard-library
  logic and preserve a concise deterministic review.
- Keep all authority false and leave the future execution lifecycle at the
  separate request, approval, authorization, and execution boundaries.

**Non-Goals:**

- Changing source code, estimator, reward, thresholds, resources, retry rules,
  gameplay policy, checkpoints, or CommunicationMod configuration.
- Rendering an execution request or delegated approval; publishing an
  authorization; loading a model or native module; constructing an environment;
  accessing a seed outcome; fitting, training, evaluating, OPE, gameplay,
  qualification, promotion, or policy-quality claims.

## Decisions

### Keep the readiness source and publication identities distinct

The registration uses `ffd9acc...` as `repository_commit` because the r5 report
and complete source inventory bind that implementation. It uses `0c62aff...` as
the readiness publication commit because that later commit contains all exact
publication and verification bytes. The current pushed head must descend from
both, but neither identity is rewritten to the registration publication commit.

Alternative: register the eventual registration commit as the execution source.
Rejected because the r5 report does not bind that later commit and the builder
correctly requires report source equality.

### Build only the existing compact v2 schema

Use `build_readiness_bound_registration` with the exact canonical repository
paths:

- `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r5/readiness_report.json`
- `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r5/candidate_seed_inventory.json.gz`
- `reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/ffd9acc444258483d172529eccfe8ccb05c9bb9b/attempt_verified.json`

The registration retains the complete 8x64 schedule but references, rather than
embeds, the 347,575,355-byte canonical candidate inventory. New v1 construction
remains disabled.

Alternative: copy or decompress the full candidate into the registration.
Rejected because it defeats the compact transport contract and exceeds the
existing artifact boundary.

### Reobserve inert external identities before publication

Hash the configured native module and provenance, current Windows CPU runtime
metadata, CommunicationMod config bytes, and complete production-checkpoint
tree without importing or loading them. The registration output root is
`D:/PycharmProjects/slay-the-spire-ai/reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2`
and must remain absent during registration publication.

Alternative: copy the 20260806-r1 external identities without reobservation.
Rejected because configuration, checkpoints, or native bytes may have changed.

### Publish registration and review, not an execution chain

Write canonical JSON to
`reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_registration.json`.
The review records artifact size/digest, canonical registration digest, exact
source/publication/readiness identities, producer and independent validation,
schedule and authority summaries, import delta, output-root absence, and explicit
false downstream operations. It does not contain a request, approval, or
authorization.

Alternative: render the request and delegated approval immediately to reduce
commits. Rejected because the lifecycle contract makes registration review an
irreversible boundary of its own.

### Do not rerun the long commit gate for evidence-only bytes

Run strict OpenSpec validation, canonical JSON/integrity checks, source-only
producer and independent registration validation, import-isolation probes, and
the focused compact-registration tests. Invoke the repository commit gate only
if implementation or test source changes unexpectedly; otherwise the recent
source commit gate and r5 focused verification remain the applicable code
evidence. No gameplay validation is applicable because no gameplay behavior is
changed or launched.

## Risks / Trade-offs

- **An external identity changes between observation and later execution** ->
  The future execution preflight reobserves every identity and fails before
  dependency loading; the registration is not edited.
- **A plan or evidence commit is confused with the registered source** -> Keep
  `repository_commit`, readiness publication commit, and registration
  publication commit as separately named fields in the review.
- **Independent validation accidentally imports runtime dependencies** ->
  Snapshot loaded Torch/native module names before validation and reject any
  newly loaded dependency.
- **A registration defect is found after push** -> Preserve r2 as immutable and
  create a new registration proposal/identity; never alter the cohort or terms.

## Migration Plan

1. Commit and push the complete OpenSpec planning artifacts without editing any
   registered implementation source.
2. Recheck r5 publication bytes, source ancestry, path absence, native/runtime/
   isolation identities, and absence of user revocation.
3. Build the compact registration into an untracked staging path, validate it
   through producer and independent verifier logic, and atomically publish the
   canonical registration plus review only if all checks pass.
4. Run focused source-only verification and strict OpenSpec validation; review
   the exact staged scope.
5. Commit and push the registration evidence while the OpenSpec change remains
   active, then confirm the exact registration is present on `origin/master`.
6. Mark the publication boundary complete, sync the delta requirement, record
   project direction, archive the completed change, and commit and push that
   closeout separately.
7. Start no empirical work. A later change may separately propose one exact
   execution request using the pushed registration.

Before step 5, rollback deletes only additive untracked registration candidates.
After push, rollback is preservation plus a new identity, not mutation.

## Open Questions

None. The user's standing delegation can simplify a later exact approval, but it
does not collapse the registration, request, authorization, or execution stages.
