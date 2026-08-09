## Context

The r1 inventory request bound source commit `5cbc6960f`, request
`d6016a7e...`, authorization `51555849...`, and launch observation
`3f006cbf...`. Its sole build invocation failed while parsing the tracked path
`reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r3.5777eef4a43065e6246481926f95d6cfcba04c88.staging/candidate_seed_inventory.json.gz`.
The current classifier recognizes only the current card-acceptance prefixes and
output-root-derived siblings, so that earlier generated root reached gzip/JSON
parsing. Cohort selection, output staging, publication, native loading, and
environment seed access did not occur.

## Goals / Non-Goals

**Goals:**

- Exclude generated report roots before artifact-format handling and blob reads.
- Cover staging, scratch, sealed, temporary, and attempt path shapes without
  depending on one experiment prefix.
- Preserve ordinary historical evidence through explicit negative tests.
- Keep the r1 attempt terminal and produce a reviewed future-identity go/no-go.

**Non-Goals:**

- Retrying, resuming, repairing, or replacing r1.
- Selecting or publishing a new cohort in this repair change.
- Reading simulator seeds, loading native/Torch/model/runtime code, or changing
  gameplay, CommunicationMod, checkpoints, policy, objective, or training.
- Broad cleanup of historical tracked or untracked reports.

## Decisions

### Classify the direct `reports/` ancestor before blob access

For each tracked report file, inspect every ancestor and identify the direct
child of `reports/`. A hidden direct child whose name ends with `.staging`,
`.scratch`, `.sealed`, `.temporary`, or `.tmp` is a generated root. A direct
child ending in `_attempts` is an attempt root. Existing exact candidate-output
and card-acceptance-prefix rules remain in place.

Classification stays in `_list_registered_source_paths`, before
`_artifact_format`, `_unsupported_seed_candidate`, and `_git_blob_batch`. Tests
replace the blob reader with a forbidden sentinel to prove generated files are
not opened.

Alternative: add the one observed readiness prefix. Rejected because another
historical experiment prefix could reproduce the same failure. Alternative:
ignore malformed JSON. Rejected because malformed ordinary registered evidence
must remain fail closed.

### Keep exclusions path-shaped and test negative boundaries

The generic rule applies only to directories directly below `reports/`, not to
ordinary files such as `reports/history/staging-result.json`, nested directories
named `staging`, or names that merely contain `attempt`. Candidate-output rules
remain exact to the registered output and successor prefixes.

Alternative: exclude every path containing staging/scratch/attempt text.
Rejected because it could silently remove legitimate historical seed evidence.

### Treat r1 as immutable terminal evidence

The pushed launch/failure/review artifacts remain unchanged. The repair report
binds the failing path and tests, records that r1 cannot run again, and decides
only whether a new proposal may preregister a distinct source/request identity.
No repair result itself grants inventory, native, model, training, evaluation,
gameplay, qualification, or promotion authority.

## Risks / Trade-offs

- [Risk] A generic suffix could exclude a legitimate direct report directory.
  -> Mitigation: restrict matching to direct children of `reports/`, require
  exact suffix forms, and retain negative eligibility tests.
- [Risk] Fixing the scanner could be mistaken for permission to retry r1.
  -> Mitigation: bind the consumed request/authorization/launch digests in the
  report and keep any future build behind a separate proposal and identity.
- [Risk] A different generated naming convention remains unrecognized.
  -> Mitigation: fail closed on malformed/unsupported ordinary evidence and add
  only evidence-backed path shapes, rather than broad content suppression.

## Migration Plan

1. Add RED path-classification and no-blob-access regressions.
2. Implement the minimal direct-root classifier and run affected source-only
   tests, compile checks, strict OpenSpec validation, and independent review.
3. Publish the repair report and future-identity go/no-go, sync/archive the
   repair change, and push one cohesive source-only boundary.
4. On rollback before commit, discard only this change's uncommitted edits. The
   r1 failure evidence is already pushed and is never removed or rewritten.

## Open Questions

None. Any future inventory build requires a separate reviewed proposal.
