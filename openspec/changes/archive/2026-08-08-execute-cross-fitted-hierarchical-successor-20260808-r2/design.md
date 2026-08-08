## Context

Commit `27a457aa71c280402d84168d012ada61168cdc27` closes the
registration/request/delegated-approval/authorization chain on
`origin/master`. The exact identities are registration file SHA-256
`9d792cadbece4ea21768386904633ebded2e94525fb186bdcbf4a4d7729dbdf9`,
request SHA-256
`6257a36c6573c8c412bb8727736e81b063dd0c7076f1ea5b41a70d4a08206c2e`,
approval SHA-256
`3786717abcbc82ab4c70a39ae8151feee09cc19f7f44f1cfa5a14257ac25901e`,
and authorization SHA-256
`80dffa2fa2c1d1a9d68d638276c73730415842f085c7d881609a37114d88152f`.
The registered output root is absent and no empirical seed has been accessed
under this identity.

The runner already implements source/native/isolation preflight, exclusive
lease, durable first-seed marker, append-only access journal, resource ledger,
chunk checkpoints, one post-start infrastructure resume, terminal publication,
and independent verification. This change invokes those existing bytes; it
does not modify them.

## Goals / Non-Goals

**Goals:**

- Consume the exact pushed authorization at most once for its logical identity.
- Preserve all 512 scheduled primary trajectories and the 64-access resume
  reserve, resource ceilings, eight-update ceiling, and family-saturation gate.
- Keep monitoring outside the active output root until the true execution
  process exits.
- Independently validate the terminal bundle and classify the mechanism result
  without claiming policy value.

**Non-Goals:**

- Changing source, native/runtime identity, schedule, folds, estimator,
  objective, reward, model initialization, optimizer, threshold, resource,
  output, authority, or lifecycle terms.
- Loading production checkpoints, running canary/holdout evaluation, OPE,
  gameplay, Slay the Spire, or CommunicationMod.
- Tuning, retrying an algorithm failure, replacing a seed, promoting a policy,
  or declaring formal RL ready.

## Decisions

### Invoke the real execute path under isolated Windows Python

Use `D:\anaconda\envs\stsai\python.exe -I -c` with a bootstrap that removes
only the explicit repo-root bootstrap argument, inserts that exact root into
`sys.path`, imports the tracked control-plane `main`, and calls `main()` with no
explicit argv. The remaining real process argv is:

`execute --repo-root <repo> --registration <exact registration> --request
<exact request> --approval <exact delegated approval> --authorization <exact
authorization>`.

Alternative: call `main(sys.argv[1:])`. Rejected because the execute branch
correctly blocks injected argv. Alternative: invoke the script file directly
under `-I`. Rejected because isolated mode removes the repo package root.

### Perform complete source-only preflight before the one execution call

Before launch, require HEAD/origin equality, exact Git blobs and canonical
digests, complete producer and independent validation, source/import isolation,
registered-output absence, exact native file/provenance identity, and no
running same-identity process. Preflight does not load native, Torch, model, or
environment code.

Alternative: rely only on executor preflight. Rejected because an externally
reviewable pre-launch boundary should detect path or publication drift before
the irreversible call, while the executor still repeats all authoritative
checks.

### Treat one shell cell as the execution owner

Launch one long-lived command with an outer timeout greater than the 14,400
charged-second ceiling plus source-control and terminal-publication overhead.
While it runs, use only the shell-cell completion signal and, if needed, a
read-only true-process liveness query. Do not list, hash, open, or mutate the
registered output root until the true Python child has exited.

Alternative: tail journals for progress. Rejected because reading an active
root can race atomic publication and previously caused a monitoring deviation.

### Apply the registered recovery rules literally

A pre-start failure before the first-seed marker may be manually re-entered only
with the identical source-bound setup if the runner declares it eligible. After
the marker, only one infrastructure interruption may resume the same logical
identity and incomplete registered chunk. Algorithm, integrity, resource,
saturation, or ordinary terminal failure is never retried.

Alternative: make all failures non-retryable. Rejected because the current
tested lifecycle deliberately distinguishes harmless pre-start re-entry and one
bounded infrastructure resume from evidence-driven retry.

### Verify only after true process exit

After exit, acquire the output lease through the independent verifier and
validate the complete inventory, source/native/isolation identity, access and
resource accounting, baselines, advantages, gradients, checkpoints, terminal,
and manifest. Publish a separate read-only postmortem and do not reinterpret a
valid negative result as policy quality.

## Risks / Trade-offs

- **The native module fails to load** -> Preserve the typed pre-start result;
  do not change DLL, path, environment, or registration inside this identity.
- **The outer wait ends while Python remains alive** -> Query true child
  liveness only, keep the active root unread, and continue waiting or apply the
  exact registered interruption rule.
- **The run reaches the 14,400-second ceiling before a complete chunk** ->
  Preserve the terminal resource failure; do not raise the ceiling or rerun.
- **A crash occurs after first seed access** -> Resume once only if durable
  evidence and the runner prove the same-identity infrastructure condition;
  otherwise preserve terminal failure.
- **The policy saturates again** -> Treat the registered saturation terminal as
  valid mechanism evidence, not as grounds for tuning or retry.

## Migration Plan

1. Strictly validate, commit, and push this execution plan while output remains
   absent.
2. Revalidate the complete pushed control chain and source-only preflight.
3. Invoke the exact execution command once and monitor liveness only.
4. After true process exit, independently verify and preserve the terminal
   bundle. Apply only a contractually eligible same-identity recovery if needed.
5. Publish a postmortem, run focused terminal tests and strict OpenSpec, sync
   the requirement, update project direction, archive, and push closeout.
6. Stop. Any policy-quality evaluation or later training requires a new
   proposal based on the terminal evidence.

Before the first-seed marker, cancellation preserves the exact setup or removes
only an unconsumed additive root when the contract permits. After the marker,
all artifacts are immutable evidence and rollback never changes a term or reruns
the algorithm.

## Open Questions

None.
