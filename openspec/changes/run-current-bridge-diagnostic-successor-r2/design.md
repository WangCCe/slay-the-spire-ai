## Context

The v1 diagnostic is a consumed, canonical zero-row failure. Its 1,824-line
runner currently embeds one registration path, output path, schema family,
preimplementation binding, and evidence inventory as module globals. The
candidate-schema fix changed the runner source without changing v1 artifacts;
direct no-native artifact recomputation remains valid, while source-bound v1
preflight correctly cannot be reused.

The anti-retry review allows one new successor only because v1 failed before
its first transition on a deterministic runner-contract defect, the defect was
fixed independently, and the proposed controls use the same already consumed
development seeds. The design must preserve v1 as a failed identity and avoid
both a full runner copy and a broad experiment-framework refactor.

## Goals / Non-Goals

**Goals:**

- Represent v1 and r2 publication identity through one small immutable profile
  boundary while sharing the existing diagnostic semantics.
- Recompute v1 canonical artifacts byte-for-byte without native loading after
  the refactor.
- Bind r2 to the consumed failure, anti-retry decision, candidate-schema fix,
  exact current source and external inputs before environment construction.
- Execute at most one pushed r2 registration and publish a deterministic
  terminal, support-limited, failed, interrupted, or passed result.

**Non-Goals:**

- No generic experiment framework, runner copy, policy or bridge behavior
  change, simulator/module rebuild, new seed, threshold change, or support
  expansion.
- No fresh evidence, baseline-floor study, readiness promotion, gameplay,
  CommunicationMod edit, OPE, model fitting, reward work, formal RL, training,
  qualification, policy/model loading, or promotion.
- No v1 repair, same-identity retry, artifact rewrite, or r3 preparation.

## Decisions

### Use one explicit immutable profile object

Introduce a frozen profile value containing only publication identity:
registration and output paths, schema versions, preimplementation binding,
implementation-source inventory, and lineage mode. Pass it explicitly through
registration, execution-result, publication, and verification helpers. Keep
cohort, policy, support, transition, and verdict semantics shared because r2
does not change them.

The existing public helper behavior defaults to the v1 profile where needed for
historical tests. New `prepare-r2`, `execute-r2`, and `verify-r2` CLI paths select
r2 explicitly. An unrecognized or mixed profile fails before environment
construction.

Alternative: copy and rename the runner. Rejected because it duplicates more
than 1,800 lines and makes future defect comparison ambiguous.

Alternative: replace all module globals with a generic experiment framework.
Rejected because that exceeds the one-diagnostic scope and adds migration risk
without improving the registered structural question.

### Bind r2 through a frozen preimplementation lineage record

Create one canonical tracked r2 preimplementation record after the planning
commit. It binds the consumed v1 registration, closeout, canonical inventory
and failure coordinates; the anti-retry review; the archived schema fix and
source commit; all predecessor evidence already required by v1; the exact
native module; and the unchanged cohort rationale. The r2 registration binds
that record by path, size, and SHA-256 and also binds the implementation commit
and source aggregate.

This keeps lineage reviewable without expanding the runtime registration into
an ad hoc evidence crawl. All paths are fixed; untracked report discovery is
forbidden.

Alternative: infer lineage from Git history at execution time. Rejected because
history alone does not bind the canonical working-tree evidence inventory.

### Separate offline implementation, preregistration, and execution commits

The implementation commit contains profile support, regressions, and the
frozen preimplementation record but no r2 registration. After focused tests,
historical recomputation, the partitioned commit gate, and strict OpenSpec
validation pass, a later clean pushed commit may publish the r2 registration.
Execution is permitted only from that pushed commit with an absent r2 output
root and a durable started journal.

This maintains a reviewable boundary despite the user's standing authorization
to continue. It prevents source edits and native execution from sharing one
identity transition.

### Preserve fixed semantics and fail closed on any profile drift

R2 keeps all v1 seeds, order, replay count, decision and wall limits, Current
policy settings, declared Courier blocker, row schema, category coverage, and
verdict precedence. Profile-specific schema names distinguish publications but
do not reinterpret rows. A partial or failed r2 result is terminal; the change
cannot create r3.

## Risks / Trade-offs

- [Risk] Threading a profile through publication helpers changes many call
  sites. -> Mitigation: add reverse tests first, keep v1 defaults, and require
  byte-identical direct recomputation of the committed v1 directory.
- [Risk] A mutable or incomplete profile could mix v1 and r2 identities. ->
  Mitigation: use a frozen value, validate exact supported profiles, and test
  cross-profile registration/output/schema rejection before environment
  construction.
- [Risk] R2 can fail on another native boundary and still not unblock baseline
  readiness. -> Mitigation: preserve exact first failure and stop; do not tune,
  repair, or prepare r3 in this change.
- [Risk] Infrastructure work continues to dominate policy evidence. ->
  Mitigation: reject full runner duplication and broad generalization; if the
  profile extraction cannot remain narrow, record `no-go` and pause the lane.
- [Trade-off] The same reused seeds have no fresh-evidence value. This is
  intentional: r2 answers only structural closure and cannot support policy
  quality or baseline-floor estimates.

## Migration Plan

1. Freeze and commit planning plus r2 preimplementation lineage with v1 bytes
   rechecked.
2. Add red dual-profile and production-candidate regressions.
3. Implement the narrow profile boundary and pass no-native verification for
   v1 and synthetic r2 fixtures.
4. Run focused verification, the partitioned commit gate, strict OpenSpec
   validation, and exact evidence hashes; commit and push implementation.
5. Prepare, review, commit, and push exactly one r2 registration with no output
   root.
6. Run the registered r2 command once, verify it in a fresh no-native process,
   close out, sync, and archive. Any interruption or failure remains terminal.

Before step 5, rollback can remove the unconsumed r2 implementation normally.
After the r2 journal exists, rollback preserves registration, journal, and all
published or partial evidence.

## Open Questions

None. Any newly discovered need to change seeds, limits, support semantics,
policy behavior, or external module bytes stops this change and requires a
separate proposal.
