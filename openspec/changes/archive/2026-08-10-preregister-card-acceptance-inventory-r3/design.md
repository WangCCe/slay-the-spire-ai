## Context

r1 terminated after its started boundary while parsing a generated readiness
root. r2 added generated-root classification, a path-only preflight, and a
durable request-bound receipt, but its sole registered process failed before
authority validation because `python -I <script>` could not import the control
module. No r2 receipt, output, staging root, candidate blob read, seed
discovery, cohort, or registration exists.

The isolated entrypoint was subsequently repaired and pushed at
`3dd915e7c51591f71179254ad616b5588b0347ae`. The exact production command now
emits a canonical binding with script SHA-256
`a47567db10fc713cf4670353e5f51b29be087cef58bfbdb462ff1447700f316f`
and control-contract SHA-256
`69efdcb18fc16e65715ff38f2a4985f49cade47bdfa734e299874031007605a2`.
The parent empirical-successor task 6.2 remains incomplete because neither
failed identity published an independently verified registration.

The current `build_inventory` implementation validates authority, source
inventory, pushed ancestry, tracked cleanliness, and output absence before
calling `_start_inventory_once`. The exclusive receipt precedes historical path
discovery, blob reads, and cohort selection. The code therefore already
supports a receipt-defined logical start; r2's stronger process-invocation cap
was a proposal constraint, not an implementation requirement.

## Goals / Non-Goals

**Goals:**

- Publish one distinct r3 identity bound to the pushed isolated-dispatch repair.
- Prove exact dispatch and source/path readiness before authority publication.
- Use the durable receipt as the sole logical one-shot boundary without
  silently retrying or mutating a failed pre-start command.
- Build, independently reconstruct, and register exactly `512/128/512` fresh
  seeds with every downstream authority false.
- Update parent task 6.2 only after successful registration review.

**Non-Goals:**

- Editing the inventory/control/verifier implementation, cohort counts,
  selection order, thresholds, or historical source semantics.
- Loading native modules, models, checkpoints, Torch runtime, or environments.
- Training, canary, holdout, evaluation, OPE, gameplay, CommunicationMod,
  qualification, promotion, or parent task 6.3.
- Reusing or modifying r1/r2 request-bound authority artifacts.
- Treating the currently unqualified five-minute commit gate as r3 evidence.

## Decisions

### Bind r3 to the isolated-dispatch source boundary

The r3 source commit is
`3dd915e7c51591f71179254ad616b5588b0347ae`. Before request publication, run
the exact production interpreter, repository working directory, `-I`, fixed
seed-inventory script, and `check-dispatch`; require byte-identical canonical
output across the reviewed observation and launch preflight. The observation
binds the interpreter, cwd, command tuple, isolated flag, script path/digest,
control module/path, and control-contract digest.

The r3 source inventory must independently reproduce the same seed-inventory
script digest and source commit. The path-only preflight binds that inventory,
both terminal predecessors, candidate path-set identity, generated-root
classifications, current pushed/clean state, and absent r3 output, staging,
attempts, and receipt paths without reading candidate blobs or seed values.

Binding only the current HEAD was rejected because report-only publication
commits advance HEAD. Current HEAD must instead equal pushed `origin/master`,
remain tracked-clean, descend from the fixed source commit, and reproduce the
fixed source inventory.

### Make receipt creation the logical one-shot boundary

A process that fails before `started.json` exists has not necessarily started
empirical inventory work. It does not consume r3 solely because a process was
created, but it is not automatically retried. First publish a bounded
`noncombat-card-acceptance-empirical-successor-prestart-failure-v1` artifact and
independent review. The artifact binds the exact command/exit/phase, source,
request, approval, authorization and launch digests; before/after output,
staging, attempts and receipt identities; registered repository/temp paths;
candidate-blob/seed/cohort access flags; tracked-file status; live child
process observation; cause classification; and its canonical self-digest.

The review must prove that execution stopped before `_start_inventory_once`,
all registered write surfaces are unchanged or absent, no unexpected child
remains, and candidate blobs, seeds, and cohorts were not accessed. Any missing,
unobserved, or ambiguous side-effect surface blocks r3 and requires a distinct
successor. Only an exact external repair such as a host permission correction
may make the same request eligible again. Source, command, request, path,
approval, authorization, resource, cohort, and authority bytes remain fixed.
Because revocation state is time-dependent, the prior launch observation is
replaced only by a newly observed and reviewed launch artifact for the same
request/approval/authorization; no other bound artifact may change. The
original launch artifact remains immutable. A separate canonical
`noncombat-card-acceptance-empirical-successor-prestart-reinvocation-review-v1`
must bind the pre-start failure digest, original and replacement launch
observation digests, unchanged request/approval/authorization digests,
external-repair classification, complete side-effect verdict, and one-use
eligibility verdict. The next invocation uses the replacement launch, and any
receipt binds that replacement digest. A second pre-start failure requires a
bounded `prestart-terminal` artifact and a distinct successor rather than
another failure/replacement chain.

The request state machine is fixed as `uninvoked -> prestart-failed ->
reinvocation-authorized -> reinvocation-started`. Only one canonical
reinvocation review with `invocation_ordinal=2` may exist. Process creation for
that second invocation consumes its one-use eligibility even if no receipt is
created. A second pre-start failure closes r3 without empirical registration;
it does not authorize a third invocation of the same request.

Path-only preflight may enumerate registered Git report paths and source-only
inventory identities before authority publication. This is distinct from the
build-owned historical path discovery and candidate-blob processing in
`_build_source_registry_and_rows`, which remains strictly after receipt
creation.

Once any empty, partial, invalid, or complete receipt exists, r3 is permanently
consumed. A later source, selection, publication, or verification failure is
terminal and cannot be retried, resumed, repaired, tuned, or replaced under r3.

This replaces the r2 process-invocation cap because it consumed an identity
before the durable boundary it was designed to protect. Removing the receipt
or permitting post-receipt recovery was rejected because it would permit seed
reselection and evidence rewriting.

### Reuse the standing grant but create a fresh authority chain

Reuse only the immutable standing-delegation grant and its external-human
provenance. Create new r3 request-bound delegated approval, authorization, and
fresh launch observation. r1/r2 request, approval, authorization, launch, and
failure artifacts remain immutable evidence and cannot authorize r3.

To reduce publication overhead without weakening digest order, use these
boundaries:

1. planning-only change;
2. dispatch observation/review, source inventory, path preflight/review, and
   request/review;
3. delegated approval/review and authorization/review;
4. fresh launch observation/review after the preceding authority commit is
   pushed;
5. pre-start gate, logical build start, verification, and terminal outcome.

Every authority map permits only repository evidence reading, historical seed
discovery, and cohort materialization required by inventory. Native, model,
environment, training, evaluation, gameplay, CommunicationMod, qualification,
promotion, and downstream execution remain false.

### Freeze the exact r3 identity before build

Use output root
`D:/PycharmProjects/slay-the-spire-ai/reports/noncombat_card_acceptance_empirical_successor_20260810_r3`
and request id
`noncombat-card-acceptance-empirical-successor-20260810-r3-inventory-request-v1`.
The request keeps `max_materialized_seeds=1152` and the existing ascending
`512/128/512` selector. The build command is observed with a 3,600-second outer
wait only; that observer grants no runtime, native, model, or environment
authority.

Before launch, require the exact dispatch observation, complete 27-test owning
seed-inventory file, its isolated-dispatch regression, strict global OpenSpec,
authority/source validation, pushed/clean-tree identity, and absent output,
staging, attempts, and receipt paths. The invalidated repository `commit`
timing profile is neither rerun nor treated as a qualification gate because r3
changes no source or test behavior.

Any source or test edit discovered to be necessary stops r3 before authority
publication and moves that repair to a separate change and source identity.

### Register only independently reconstructed success

After a successful build, run the distinct `verify-inventory` command without
selection or publication authority. Independently compare source registry,
rows, exclusions, ordered cohorts, per-role digests, whole-inventory digest,
request/authorization/launch bindings, output closure, and receipt identity.

Only exact reconstruction permits one canonical r3 registration binding the
inventory digest and the 512 training, 128 canary, and 512 holdout cohorts. Its
authority and empirical-operation maps are all false. Commit and push the
inventory, verification, registration, reviews, and parent task 6.2 together.
Training request work remains a separate parent task 6.3 boundary.

The registration format is frozen before seed access as
`noncombat-card-acceptance-empirical-successor-registration-v1` with identity
`noncombat-card-acceptance-empirical-successor-20260810-r3-registration-v1`.
Its exact top-level fields are `schema_version`, `registration_id`,
`source_commit`, `source_inventory_sha256`, `output_root`, `request_sha256`,
`approval_sha256`, `authorization_sha256`, `launch_observation_sha256`,
`receipt_sha256`, `inventory_sha256`, `cohorts`, `role_sha256`, `authority`,
`empirical_operations`, and `registration_sha256`. `cohorts` and `role_sha256`
use exactly the inventory role keys and values. `authority` has exactly
`causal`, `communication_mod`, `environment_construction`, `evaluation`,
`execution`, `formal_rl`, `gameplay`, `model_fitting`, `native_loading`, `ope`,
`production_model_loading`, `promotion`, `qualification`, `seed_access`, and
`training`. `empirical_operations` has exactly `communication_mod`,
`environment_construction`, `evaluation`, `model_fitting`, `model_loading`,
`native_loading`, `ope`, `runtime_fitting`, `seed_access`, and `training`.
Every value is false; missing, unknown, duplicate, or non-boolean fields fail.
`registration_sha256` is the SHA-256 of canonical JSON for the other fields. No
outcome-dependent field or threshold may be added after build.

On any started failure, publish and independently review one bounded terminal
report, leave task 6.2 unchecked, archive r3, and grant no successor or training
authority.

## Risks / Trade-offs

- [Risk] Pre-start reinvocation is mistaken for empirical retry. -> Mitigation:
  require a bounded failure plus independent complete-side-effect review,
  unchanged request/source/authority bytes, a chained fresh revocation
  observation, and at most one reviewed reinvocation; ambiguity or a second
  pre-start failure requires a distinct successor.
- [Risk] Historical report growth introduces another malformed source. ->
  Mitigation: freeze and review the complete path set before authority; ordinary
  malformed sources still fail closed after the receipt.
- [Risk] Current HEAD advances after source publication. -> Mitigation: bind the
  pushed source ancestor and exact module inventory while requiring current
  HEAD to be pushed and tracked-clean.
- [Risk] A successful inventory is mistaken for training approval. ->
  Mitigation: registration and every downstream authority remain false; parent
  task 6.3 stays unchecked.
- [Risk] The outer observer terminates a started build. -> Mitigation: allow
  3,600 seconds for this source-only operation and treat any post-receipt timeout
  as terminal evidence without retry.

## Migration Plan

1. Strict-validate and independently review this planning-only change; commit
   and push it before producing r3 evidence.
2. Reproduce exact isolated dispatch, source inventory, terminal predecessors,
   and path/output preflight; render and review the request, then push the
   source/preflight/request boundary.
3. Resolve the immutable standing grant to r3, render/review authorization, and
   push the authority boundary.
4. Observe fresh launch-time revocation state after that push, review it, and
   push the launch boundary.
5. Build and review the frozen pre-start gate from a pushed clean base, commit
   and push it, then perform a separate no-write pushed/clean/absence recheck
   immediately before invoking one logical build start. If a pre-start failure
   occurs, publish and review the bounded failure before any eligibility
   decision under the receipt-defined rule.
6. On build success, run distinct verification, independently reconstruct and
   publish the all-false registration, update parent task 6.2, and push.
7. On terminal failure, publish its review without registration. In either
   outcome, sync applicable delta specs, archive r3, strict-validate, and push
   closeout.

Before receipt creation, rollback removes only uncommitted r3 artifacts. After
receipt creation, rollback is immutable evidence preservation and downstream
denial, never deletion or retry.

## Open Questions

None.
