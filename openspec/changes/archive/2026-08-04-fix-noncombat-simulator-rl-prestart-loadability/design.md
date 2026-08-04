## Context

The archived r1 runner imported its experiment and policy-model modules, which
imported PyTorch before command execution; source-only preflight also reached
Torch for version inspection. It then created output and a started journal,
initialized the Torch model, and only afterward loaded the native adapter.
PyTorch had already loaded Conda's old `libwinpthread-1.dll`; Windows reused
that module when the CLion-built adapter requested its newer MinGW runtime. Two
required procedures were absent, so native loading failed before any
environment or seed access, but the runner published a terminal blocked
experiment.

Fresh-process evidence proves that the same native module loads successfully
before PyTorch and that PyTorch plus `CandidateRanker` then initialize normally.
The fix therefore concerns ordering and the definition of experiment start,
not the adapter binary, simulator source, model, reward, or cohorts.

## Goals / Non-Goals

**Goals:**

- Make native/Torch compatibility validation precede the started journal and
  all empirical work.
- Leave fresh output absent when pre-start validation fails.
- Load native before restoring Torch state on resume and preserve the last
  complete evidence when pre-rollout resume validation fails.
- Preserve the current one-shot and terminal rules after the started journal.
- Keep historical r1 verification byte-compatible.

**Non-Goals:**

- No retry, repair, reclassification, or artifact mutation for r1.
- No static relink, adapter rebuild, dependency installation, environment
  mutation, seed selection, successor registration, or experiment execution.
- No live gameplay, Communication Mod, production checkpoint, policy, reward,
  threshold, or promotion change.

## Decisions

### Define experiment start by durable output initialization

A fresh invocation keeps runner and experiment imports Torch-free, reads the
installed Torch version from package metadata, then performs source/control
preflight, native loading, native provenance validation, and pristine CPU
training-runtime initialization while the registered output path remains
absent. Only after all steps pass may it call `initialize_experiment_output`,
whose atomic directory creation and first journal record define the start of
the logical experiment.

Repeated validation before that boundary is not an experiment retry because it
constructs no environment, accesses no seed, records no trajectory, and
produces no experiment artifact. Once the started record exists, all existing
no-retry, resume, wall-time, cohort, and terminal semantics continue unchanged.

Alternative: preserve the current boundary and issue a new logical id for every
startup failure. Rejected because infrastructure compatibility contributes no
empirical evidence and unnecessarily consumes preregistered attempts.

### Load native before Torch in the execution process

The experiment module lazily imports `CandidateRanker`, `FeatureConfig`, and
`candidate_feature_vector` only from functions that already require Torch. For
a fresh start, `load_native_module` and post-load provenance validation run
before `initialize_training_runtime`. The pristine runtime created by that
validation becomes the actual fresh runtime; it is not discarded and recreated
after output initialization.

For a resume, the runner acquires the existing execution lease, recovers any
pending atomic chunk, loads and validates native, and only then calls
`resume_training_runtime_from_output`. Thus both fresh initialization and
checkpoint restoration import Torch after the intended MinGW runtime is loaded.

Alternative: statically link the MinGW runtime into a rebuilt adapter. Rejected
for this repair because it changes the native binary and build contract, while
the demonstrated native-first order solves the collision without rebuilding or
adding dependencies. Static linking can be evaluated separately if another
consumer cannot control import order.

### Keep pre-rollout validation failures non-mutating

Native load, provenance, pristine runtime initialization, and resume restoration
remain outside the broad exception handler that publishes a terminal result.
Their failure returns a blocked command status but writes no fresh terminal
record. Fresh output stays absent; resumable output retains its last complete
journal/checkpoint.

Failures raised after the runtime is ready and the rollout/evaluation body has
started retain the current exact-coordinate terminal publication behavior.
This keeps simulator, action, numeric, and support-envelope failures fail-closed.

Alternative: add a new preflight artifact or CLI phase. Rejected because the
same in-process order must still be enforced by `execute`; a second artifact
would duplicate the check without strengthening the execution boundary.

### Preserve historical verification and authority

The change does not modify registration, authorization, terminal artifact, or
standalone-verifier schemas. The archived r1 verifier resolves its bound source
commit and remains authoritative. Project direction records only that future
executions have a corrected start boundary; it grants no successor authority.

## Risks / Trade-offs

- [Risk] Native-first MinGW DLLs could affect PyTorch. -> Mitigation: the audit
  directly initialized PyTorch 2.5.1 and `CandidateRanker` after native load;
  add an ordering regression and retain the CPU-only runtime checks.
- [Risk] Two fresh invocations pass pre-start validation concurrently. ->
  Mitigation: `initialize_experiment_output` uses absent-path creation; only one
  process can create the registered output, and the loser has not accessed a
  seed.
- [Risk] A pre-start failure is mistaken for a positive experiment result. ->
  Mitigation: output remains absent, the CLI returns blocked, and no manifest or
  report is produced.
- [Trade-off] Pre-start work is outside the empirical cumulative wall budget.
  This is intentional because it is bounded startup validation and contains no
  rollout; operational command timeout remains available for hung tooling.

## Migration Plan

1. Add failing source-only regressions for ordering and fresh/resume failure
   boundaries.
2. Reorder the runner and reuse the pristine fresh runtime.
3. Run focused runner/artifact tests and independently verify archived r1.
4. Run the repository commit gate once, strict OpenSpec, compilation, and diff
   checks; no gameplay or native experiment execution.
5. Update project direction, sync the delta, archive, commit, and push.

Rollback reverts only runner source, tests, direction text, and this OpenSpec
change. The audit and archived r1 evidence remain immutable.

## Open Questions

None. A successor experiment, static native relink, or cohort reuse decision is
a separate change.
