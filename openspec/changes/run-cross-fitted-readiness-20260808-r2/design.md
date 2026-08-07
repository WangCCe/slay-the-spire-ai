## Context

Readiness `r1` consumed source commit
`863ae5a4046df110e4f9028bb3c56d556a7c6a43` and terminated at
`no_go_source_binding` before candidate inventory reconstruction. The defect is
closed by source commit `54b266b4ba1b4993faded5fc366532598d81b9f6` and the
repair closeout is pushed at `ab263195797038c8f29dbd6e7e540b8cbe098f33`.
Focused verification passed, the exact schedule provenance is normative in the
main spec, and the repaired auditor binds that durable spec path.

At proposal time, the source-keyed attempt directory for `ab2631957...`, the
planned `r2` output, scratch root, and this change path were all absent. The
attempt root contains only the consumed `r1` source identity. The final source
identity cannot be named until these planning artifacts and their synced delta
are committed and pushed; the resulting pushed commit is the only identity
eligible for the invocation.

## Goals / Non-Goals

**Goals:**

- Preregister one exact source-only `r2` audit identity and path set.
- Establish a pushed, tracked-clean, previously unclaimed source commit after
  all planning bytes are final.
- Invoke the existing auditor at most once only after every preflight remains
  true.
- Independently verify and preserve either its canonical publication or
  terminal receipt, with all authority false.

**Non-Goals:**

- Editing the auditor, verifier, seed selection, budget, rehearsal, or decision
  contract.
- Retrying or replacing `r1`, or reusing its source commit, audit id, paths, or
  receipts.
- Registering or running an empirical successor, native adapter, runtime,
  model, training, evaluation, OPE, gameplay, CommunicationMod, qualification,
  or promotion.
- Treating a readiness `go` as policy-quality, causal, live-value, formal-RL,
  or execution evidence.

## Decisions

1. **Use one immutable planning commit as source identity.** The delta is
   synced to the canonical main spec, planning artifacts are strictly
   validated, and the plan is committed and pushed. Only then is the exact
   40-character `HEAD == origin/master` value inserted into the command. No
   post-commit file records that hash before invocation; the command and
   source-keyed started receipt are the canonical binding.

2. **Fix every caller-controlled identifier before source commit.** The audit
   id is
   `noncombat-cross-fitted-empirical-successor-readiness-20260808-r2`, output is
   `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r2`,
   and scratch is `.source_only_readiness_scratch_20260808_r2`. For source
   commit `S`, the only allowed staging sibling is
   `reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r2.S.staging`.
   These values cannot be changed after preflight or after an attempt claim.

3. **Require a final source-only preflight immediately before invocation.** It
   rechecks exact pushed identity, tracked cleanliness, source-keyed attempt
   absence, output absence, scratch absence, exact derived staging absence,
   canonical bound-path existence, and preservation of the `r1` receipts. Any
   failure stops without invoking the auditor or substituting another
   source/path.

4. **Run only the existing isolated command.** The invocation is:

   ```text
   D:\anaconda\envs\stsai\python.exe -I D:\PycharmProjects\slay-the-spire-ai\analysis_scripts\noncombat_cross_fitted_empirical_successor_readiness.py --repo-root D:\PycharmProjects\slay-the-spire-ai --source-commit <pushed-plan-commit> --scratch-root D:\PycharmProjects\slay-the-spire-ai\.source_only_readiness_scratch_20260808_r2 --output-dir D:\PycharmProjects\slay-the-spire-ai\reports\noncombat_cross_fitted_empirical_successor_readiness_20260808_r2 --audit-id noncombat-cross-fitted-empirical-successor-readiness-20260808-r2
   ```

   The command is launched with
   `cwd=D:\PycharmProjects\slay-the-spire-ai`; the absolute script path is
   nevertheless normative so script resolution does not depend on that cwd.
   The outer command may wait up to 7,200 seconds, but it does not widen any
   auditor stage, verifier, artifact, or budget ceiling. An outer timeout is not
   terminal evidence; true Python-child absence and lease state must be checked
   before any output inspection.

5. **Treat the source-keyed claim as irreversible.** Once `attempt_started.json`
   exists, every exit, exception, timeout, no-go, or publication failure
   consumes that source identity. There is no retry, resume, repaired rerun,
   alternate path, new audit id, wider limit, or same-source invocation.

6. **Verify after process exit only.** If a canonical output was installed, the
   standalone standard-library verifier rechecks it against the pushed source.
   If no output exists, a separate Python `-I` standard-library receipt review
   executes the following exact algorithm without importing the auditor,
   publication verifier, Torch, native, runtime, model, or project modules:

   1. Accept only the final 40-character source commit `S` as input and derive
      the fixed attempt, output, scratch, and staging paths from decisions 2 and
      4; do not accept path or audit-id overrides.
   2. Require the attempt directory to contain exactly the two regular files
      `attempt_started.json` and `attempt_terminal.json`, each at most 1 MiB;
      reject `attempt_verified.json` and every additional entry.
   3. Decode strict UTF-8 JSON with duplicate object keys rejected. For each
      file, require byte equality with
      `json.dumps(value, allow_nan=False, ensure_ascii=True,
      separators=(",", ":"), sort_keys=True).encode("utf-8") + b"\\n"`.
   4. Require the started receipt to have exactly the fields emitted by
      `noncombat-cross-fitted-empirical-successor-readiness-attempt-v1`, with
      the fixed r2 audit id, `S`, fixed absolute output/scratch/staging paths,
      status `started`, the exact 18 readiness authority keys all false, and
      the exact 10 empirical-operation keys all false. Recompute
      `attempt_sha256` as SHA-256 of the canonical started body after removing
      only `attempt_sha256`.
   5. Require the terminal receipt to have exactly `attempt_sha256`,
      `audit_id`, `authority`, `decision`, `empirical_operations`, `failure`,
      `schema_version`, `source_commit`, `status`, and `terminal_sha256`;
      require exact linkage to the started receipt, schema
      `noncombat-cross-fitted-empirical-successor-readiness-attempt-terminal-v1`,
      status `terminal_no_go`, the same exact all-false maps, one and only one
      failed gate from `source_binding`, `cohort_not_fresh`,
      `rehearsal_boundary`, `control_plane_scaling`, `budget_binding`, or
      `artifact_binding`, decision status `no_go`, reason `no_go_<gate>`, and a
      failure object containing exactly nonempty string `message` and `type`
      fields with message length at most 2,000 characters. Recompute
      `terminal_sha256` from the canonical terminal body after removing only
      `terminal_sha256`.
   6. Require output, scratch, and exact derived staging to be absent, and
      require no sealed sibling matching
      `.noncombat_cross_fitted_empirical_successor_readiness_20260808_r2.*.sealed`.
      Recompute and report the raw SHA-256 and byte size of both receipt files.
   7. Emit one canonical JSON summary containing `audit_id`, `source_commit`,
      `attempt_sha256`, `terminal_sha256`, raw receipt bindings, decision,
      `all_authority_false=true`, `all_empirical_operations_false=true`, and
      `status=terminal_receipts_independently_verified`. Any failed check exits
      nonzero, leaves the terminal unverified, and never authorizes a retry.

## Risks / Trade-offs

- **A remaining source-only defect consumes another identity.** The immutable
  one-shot rule is more important than recovering this run; any defect becomes
  evidence for a new source change, not a retry.
- **Planning bytes change the source commit.** Final preflight deliberately uses
  the post-push hash rather than the proposal-time hash.
- **The audit can be long.** A 7,200-second outer wait prevents premature shell
  interruption while leaving all internal ceilings unchanged.
- **A valid `go` can be overinterpreted.** Reports and project direction retain
  all empirical, training, policy, and promotion authorities as false.

## Migration Plan

1. Complete and strictly validate this change, sync its delta, and run only the
   focused source-only regression needed to prove the bound paths still exist.
2. Commit and push the planning bytes; record exact `HEAD == origin/master`.
3. Perform the final absence and source-identity preflight.
4. Invoke the exact command once if and only if preflight passes.
5. Wait for true process exit, independently verify the resulting publication
   or terminal receipts, and update project direction.
6. Sync/archive the completed execution change and push evidence. Never rerun
   the auditor under the consumed source identity.

Before the claim, rollback means abandoning the run. After the claim, rollback
is not defined; only terminal preservation and a later new proposal are valid.

## Open Questions

None. The readiness outcome, not this plan, decides whether an empirical
successor registration may later be proposed.
