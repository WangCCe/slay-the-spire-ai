## Context

Readiness r2 consumed source commit
`522185d06ddf48cb1be095c16efacaad299a0197` and published an independently
verified `go`. Compact-registration implementation commit
`08d2c74e6e923380f32bc8aa5aa75c8c337f27d7` subsequently changed the control
plane, seed helper, terminal verifier, and canonical successor spec. Those
changes are pushed and their complete focused files pass, but source identity
is part of readiness evidence, so r2 cannot authorize a registration built by
the new source.

At proposal time, the planned r3 output and scratch paths, every r3 staging
sibling, and an attempt directory keyed by the compact implementation commit
are absent. The r2 output and verified source-keyed receipt remain present. The
final source identity cannot be named until these planning artifacts and their
synced delta are committed and pushed; that final commit must descend from and
preserve `08d2c74e6e923380f32bc8aa5aa75c8c337f27d7`.

## Goals / Non-Goals

**Goals:**

- Preregister one exact source-only r3 audit identity and path set.
- Establish one pushed, tracked-clean, previously unclaimed source commit that
  contains the complete r3 plan and unchanged compact implementation.
- Require a separate exact human authorization after that commit is known.
- Invoke the existing auditor at most once only after every preflight remains
  true.
- Independently verify and preserve either its canonical publication or
  terminal receipt, with all authority false.

**Non-Goals:**

- Editing the auditor, verifier, seed selection, compact-registration code,
  budget, rehearsal, or decision contract.
- Retrying or replacing r1 or r2, or reusing either source identity, audit id,
  path, receipt, publication, or eligibility claim.
- Creating an empirical-successor registration or execution request.
- Loading a native adapter, runtime, Torch, model, checkpoint, game, or
  CommunicationMod; accessing an empirical outcome; fitting; training;
  evaluating; running OPE; qualifying; or promoting.
- Treating readiness `go` as policy-quality, causal, live-value, formal-RL, or
  execution evidence.

## Decisions

1. **Use one immutable final planning commit as source identity.** The r3 delta
   is synced to the canonical readiness spec, planning artifacts are strictly
   validated, and the plan is committed and pushed. The final source commit
   must descend from compact implementation commit
   `08d2c74e6e923380f32bc8aa5aa75c8c337f27d7`. The final preflight uses
   `git diff --name-status --no-renames` and requires the exact 16-row path and
   status manifest in the canonical readiness requirement; categories,
   prefixes, rename detection, and additional project-direction or source paths
   are not accepted. The final exact 40-character `HEAD == origin/master` value
   is the only identity eligible for invocation. No post-commit file records
   that self-referential hash before invocation; the exact authorization,
   command, and started receipt bind it.

2. **Fix every caller-controlled identifier before source commit.** The audit
   id is
   `noncombat-cross-fitted-empirical-successor-readiness-20260808-r3`, output is
   `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r3`,
   and scratch is `.source_only_readiness_scratch_20260808_r3`. For source
   commit `S`, the only allowed staging sibling is
   `reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r3.S.staging`.
   These values cannot change after preflight or claim.

3. **Require a final source-only preflight immediately before authorization
   and again before invocation.** It rechecks exact pushed identity, tracked
   cleanliness, ancestry and allowed path diff from the compact baseline,
   source-keyed attempt absence, output absence, scratch absence, exact derived
   staging and sealed absence, canonical bound-path existence, the exact
   16-row source diff, and the eight size/SHA-256 r1/r2 bindings listed in the
   canonical readiness requirement. Any failure stops without invoking the
   auditor or substituting another source, path, file, or digest.

4. **Require exact human authorization for this identity.** After final
   preflight identifies `S`, the execution request must state every field in the
   canonical authorization tuple: `S`, interpreter, isolated mode, absolute
   script, repository root and cwd, complete command, audit id, output, scratch,
   source-keyed attempt, staging and sealed derivations, outer wait, all fixed
   internal ceilings and sizes, all-false maps, at-most-once claim, and no-retry
   rule. Execution remains blocked until the user explicitly approves that
   exact request. Earlier standing repository, experiment, training, push, or
   similar-run authorization is insufficient. This separates planning
   publication from empirical-adjacent source consumption.

5. **Run only the existing isolated command.** After exact approval, the sole
   invocation is:

   ```text
   D:\anaconda\envs\stsai\python.exe -I D:\PycharmProjects\slay-the-spire-ai\analysis_scripts\noncombat_cross_fitted_empirical_successor_readiness.py --repo-root D:\PycharmProjects\slay-the-spire-ai --source-commit <pushed-plan-commit> --scratch-root D:\PycharmProjects\slay-the-spire-ai\.source_only_readiness_scratch_20260808_r3 --output-dir D:\PycharmProjects\slay-the-spire-ai\reports\noncombat_cross_fitted_empirical_successor_readiness_20260808_r3 --audit-id noncombat-cross-fitted-empirical-successor-readiness-20260808-r3
   ```

   The command uses `cwd=D:\PycharmProjects\slay-the-spire-ai`; its absolute
   script path is normative. The outer command may wait up to 7,200 seconds but
   cannot widen an auditor, verifier, artifact, or budget ceiling. An outer
   timeout is not terminal evidence. The readiness runner has no top-level
   output lease, so a source-specific Windows process query must prove the exact
   auditor process and every observed descendant absent before any attempt,
   output, scratch, staging, or sealed path is inspected. A synthetic rehearsal
   child's lease is not an outer-run liveness signal.

6. **Treat the source-keyed claim as irreversible.** Once
   `attempt_started.json` exists, every exit, exception, timeout, no-go, or
   publication failure consumes the source identity. There is no retry,
   resume, repaired rerun, alternate path, new audit id, wider limit, or
   same-source invocation.

7. **Verify after process exit only from durable contracts.** If a canonical
   output is installed, the standalone standard-library verifier rechecks it
   against the pushed source. If no output exists, a separate Python `-I`
   standard-library review implements the exact field lists, schemas, canonical
   encoding, digests, false-map keys, failure gates, path absence, sealed-name
   pattern, bounds, and output schema in the canonical main readiness
   requirement. That main spec is an auditor-bound source input; no active or
   archived change file supplies runtime semantics. The review imports no
   auditor, publication verifier, Torch, native, runtime, model, or project
   module and authorizes no retry on failure.

## Risks / Trade-offs

- [A remaining source-only defect consumes the new identity] -> Preserve the
  one-shot rule and treat the defect as evidence for a later source change.
- [Planning bytes change the source commit] -> Use only the post-push clean hash
  and require compact-baseline ancestry plus an allowed-path diff.
- [The audit can be long] -> Permit a 7,200-second outer wait while leaving all
  internal ceilings unchanged and monitoring only true child liveness.
- [A valid `go` can be overinterpreted] -> Keep every empirical, training,
  policy, and promotion authority false in reports, receipts, and direction.
- [Broad standing authorization could be mistaken for this claim] -> Require a
  new exact source-keyed human approval after final preflight.

## Migration Plan

1. Complete and strictly validate this change, sync its delta, and run only the
   focused source-only checks needed to validate the frozen plan and paths.
2. Obtain independent read-only review of command, paths, authority, and
   anti-retry semantics; resolve findings without invoking the auditor.
3. Commit and push the exact 16-row planning, contract, and current-change
   closeout manifest, then record exact `HEAD == origin/master` and re-run the
   complete source-only preflight.
4. Present the exact source-keyed execution authorization and stop.
5. Only after explicit approval, invoke the exact command once, wait for true
   process exit, independently verify the outcome, and publish closeout.

Before claim, rollback means abandoning the plan. After claim, rollback is not
defined; only terminal preservation and a later new proposal are valid.

## Open Questions

None. The readiness outcome, not this plan, determines whether a later compact
registration proposal is eligible.
