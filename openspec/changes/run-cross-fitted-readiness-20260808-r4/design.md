## Context

Readiness r3 consumed pushed source
`5777eef4a43065e6246481926f95d6cfcba04c88` exactly once and terminalized as
`no_go_artifact_binding`: a prior readiness candidate recursively entered the
historical seed universe until canonical serialization crossed the unchanged
512 MiB ceiling. The runner then retained its owned staging directory, so the
otherwise canonical terminal receipts could not pass the preregistered no-
publication review. The r3 attempt, closeout, and residue are immutable and
cannot be repaired or retried.

Pushed repair commit `479f5536ca21e2abd543f33f970bef93103ba0d8`
excludes the two exact readiness-derived report namespaces before blob loading
in both producer and independent verifier, and retires only exact runner-owned
staging before terminal closure. Focused source-only tests and independent
review passed; the repository commit gate timed out once and was not retried.
The final r4 source identity cannot be named until this plan and its synced
delta are committed and pushed.

## Goals / Non-Goals

**Goals:**

- Preregister one exact repaired-source r4 audit identity and path set.
- Establish one pushed, tracked-clean, previously unclaimed source commit that
  contains the complete r4 plan and preserves the repair commit.
- Bind and preserve r1/r2 evidence plus the consumed r3 receipts, closeout, and
  residue without parsing r3 residue as historical seed evidence.
- Require a separate exact human authorization after the final source commit
  is known.
- Invoke the existing auditor at most once only after every preflight remains
  true, then independently verify a canonical publication or terminal receipt.

**Non-Goals:**

- Editing the auditor, verifier, source classifier, cleanup logic, seed
  selection, registration code, thresholds, ceilings, or decision contract.
- Deleting, moving, rewriting, independently blessing, or retrying r3.
- Creating a successor registration or execution request.
- Loading native, runtime, Torch, model, checkpoint, game, or CommunicationMod
  code; accessing empirical outcomes; fitting; training; evaluating; running
  OPE; qualifying; or promoting.
- Treating readiness `go` as policy-quality, causal, live-value, formal-RL, or
  empirical-execution evidence.

## Decisions

1. **Use one immutable final planning commit as source identity.** The r4 delta
   is synced to the canonical readiness spec, planning artifacts are strictly
   validated, and the plan is committed and pushed. The final commit must
   descend from repair commit
   `479f5536ca21e2abd543f33f970bef93103ba0d8`. The final preflight uses
   `git diff --name-status --no-renames` and requires exactly the five new r4
   change files plus the modified canonical readiness spec. The exact 40-
   character `HEAD == origin/master` value is the sole eligible source. No
   tracked file records that self-referential hash; the exact authorization,
   command, and started receipt bind it.

2. **Fix every caller-controlled identifier before source commit.** The audit
   id is
   `noncombat-cross-fitted-empirical-successor-readiness-20260808-r4`, output is
   `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r4`,
   and scratch is `.source_only_readiness_scratch_20260808_r4`. For final source
   `S`, the sole staging path is
   `reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r4.S.staging`.
   These values cannot change after preflight or claim.

3. **Bind old evidence and new absence immediately before authorization and
   invocation.** Preflight rechecks exact pushed identity, tracked cleanliness,
   repair ancestry, the exact six-row source diff, all canonical bound inputs,
   all existing r1/r2 bindings, and the exact r3 inventory recorded in the
   delta spec. It also proves absence of the r4 source-keyed attempt, output,
   scratch, exact staging path, and every matching sealed sibling. Any mismatch
   stops without invoking or substituting a source, path, file, digest, or
   limit.

4. **Require an exact source-keyed human authorization.** The execution request
   names `S`, interpreter, isolated mode, absolute script, repository root and
   cwd, complete command, audit id, all paths, outer wait, fixed internal
   ceilings and sizes, all-false authority maps, at-most-once claim, and no-
   retry rule. Earlier standing repository, training, experiment, push, or
   similar-run authorization is insufficient because it does not bind the new
   irreversible source identity.

5. **Run only the existing isolated command.** After exact approval, the sole
   invocation is:

   ```text
   D:\anaconda\envs\stsai\python.exe -I D:\PycharmProjects\slay-the-spire-ai\analysis_scripts\noncombat_cross_fitted_empirical_successor_readiness.py --repo-root D:\PycharmProjects\slay-the-spire-ai --source-commit <pushed-plan-commit> --scratch-root D:\PycharmProjects\slay-the-spire-ai\.source_only_readiness_scratch_20260808_r4 --output-dir D:\PycharmProjects\slay-the-spire-ai\reports\noncombat_cross_fitted_empirical_successor_readiness_20260808_r4 --audit-id noncombat-cross-fitted-empirical-successor-readiness-20260808-r4
   ```

   The cwd is `D:\PycharmProjects\slay-the-spire-ai`. The outer command may
   wait up to 7,200 seconds but cannot widen any internal ceiling. An outer
   timeout is not terminal evidence. A source-specific Windows process query
   must prove the exact auditor and every observed descendant absent before
   attempt, output, scratch, staging, sealed, or receipt inspection.

6. **Treat the source-keyed claim as irreversible.** Once
   `attempt_started.json` exists, every exit, exception, timeout, no-go,
   verifier failure, or publication failure consumes the source. There is no
   retry, resume, repaired rerun, alternate path, new audit id, wider limit, or
   same-source invocation.

7. **Verify only durable outcomes after process exit.** An installed output is
   checked by the standalone standard-library verifier against `S`. With no
   output, an independent Python `-I` standard-library review applies the
   canonical receipt schemas, encoding, identity, digest, all-false, bounded-
   artifact, and path-absence contract with r4 identifiers. It imports no
   auditor, verifier, Torch, native, runtime, model, or project module and never
   authorizes a retry.

## Risks / Trade-offs

- [A remaining source-only defect consumes r4] -> Preserve the one-shot rule;
  any correction requires a later proposal and new pushed source.
- [Planning bytes alter source identity] -> Use only the post-push clean hash
  and the exact repair-baseline diff.
- [Old evidence is accidentally treated as input] -> Bind r3 bytes for
  preservation while the repaired exact-prefix classifier excludes all
  readiness-derived namespaces before loading.
- [The audit is long] -> Permit a 7,200-second outer wait while leaving all
  internal ceilings unchanged and monitor true child liveness.
- [A valid `go` is overinterpreted] -> Keep every empirical, training, policy,
  and promotion authority false in publication, receipts, and closeout.

## Migration Plan

1. Complete and strictly validate this change, sync its delta, and run only
   source-only planning checks; do not invoke the auditor.
2. Obtain independent read-only review of command, paths, evidence bindings,
   authority, and anti-retry semantics.
3. Commit and push the exact six-row plan diff, record exact
   `HEAD == origin/master`, and rerun the complete source-only preflight.
4. Present the exact source-keyed authorization and stop.
5. Only after explicit approval, invoke once, wait for true process exit,
   independently verify the outcome, and publish closeout.

Before claim, rollback means abandoning the r4 plan. After claim, rollback is
not defined; only terminal preservation and a later new proposal are valid.

## Open Questions

None. The readiness result, not this plan, determines whether a later successor
registration proposal is eligible.
