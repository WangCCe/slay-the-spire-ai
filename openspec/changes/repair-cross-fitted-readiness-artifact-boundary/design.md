## Context

Readiness r3 consumed pushed source `5777eef4a43065e6246481926f95d6cfcba04c88` exactly once and terminalized as `no_go_artifact_binding`. The source tree contained the independently verified r2 candidate at `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r2/candidate_seed_inventory.json.gz`. The seed helper enumerated every structured artifact under `reports/`, parsed that candidate's 1,676,494 historical rows as new seed evidence, and attempted to embed the expanded inventory in another candidate. Streaming serialization stopped at the unchanged 512 MiB canonical ceiling.

The runner had already created its exact staging directory and partial gzip. Its generic exception path cleaned only a sealed snapshot, then wrote a canonical terminal receipt. The retained staging path caused the preregistered no-publication receipt review to fail even though receipt content, identity, hashes, and all-false maps were valid. The r3 attempt and residue are immutable evidence and cannot be repaired or retried.

## Goals / Non-Goals

**Goals:**

- Prevent cross-fitted readiness attempts, publications, closeouts, staging, and sealed artifacts from recursively becoming historical seed evidence.
- Keep producer and standalone-verifier source selection byte-independent but behaviorally identical.
- Remove only staging created and owned by the current readiness invocation before writing a terminal failure receipt.
- Preserve a durable typed no-go if cleanup itself fails, without claiming independent terminal verification.
- Add focused regressions that reproduce both r3 defects without materializing a 512 MiB test artifact.

**Non-Goals:**

- Deleting, moving, rewriting, verifying, or retrying the consumed r3 attempt or residue.
- Raising stored, canonical, verifier, stage, budget, or process ceilings.
- Changing candidate, report, receipt, registration, or terminal schemas.
- Changing legitimate empirical seed evidence, reserved ranges, ascending selection, schedule size, or consumed-cohort disjointness.
- Running readiness r4 or any native, runtime, model, empirical, training, evaluation, gameplay, or CommunicationMod operation.

## Decisions

1. **Exclude the exact readiness-derived report namespaces before blob loading.** Both seed-helper and standalone-verifier implementations classify canonical Git paths beginning with either `reports/noncombat_cross_fitted_empirical_successor_readiness_` or `reports/.noncombat_cross_fitted_empirical_successor_readiness_` as derived readiness artifacts. These prefixes cover attempts, final publications, closeouts, predictable staging, and random sealed siblings. Classification happens before format selection, blob batch reads, decompression, or seed recursion. Other report paths retain their existing format and unsupported-seed-candidate behavior.

   A basename-only exclusion was rejected because it would miss readiness JSON reports and receipts and could suppress unrelated evidence stored under a legitimate namespace. Recording excluded paths in the inventory schema was rejected because the source commit and independently reproduced Git-tree classifier already bind the universe, while a schema change would widen compatibility and verifier scope unnecessarily.

2. **Keep independent implementations and prove parity with table-driven tests.** The standalone verifier continues not to import the producer or seed helper. It implements the same two exact prefixes locally. Tests feed included, excluded, and lookalike paths to both implementations and require identical classification and resulting source bindings. This preserves the independent-verification boundary while making drift observable.

3. **Track exact staging ownership explicitly.** `run_readiness_audit` records ownership only after its exclusive `staging.mkdir()` succeeds. The exception path may remove staging only when that ownership flag is true and the path still equals the exact output/source-derived sibling. A pre-existing staging path fails source binding and is never marked owned or removed.

4. **Clean owned staging before terminal receipt publication.** On any pre-install failure after staging creation, including candidate serialization, report generation, or independent-verifier failure, the runner performs bounded removal and proves absence before terminalizing. Successful sealing retains its existing staging retirement and sealed cleanup flow.

5. **Cleanup failure remains durable and fail-closed.** If exact owned staging cannot be removed or absence cannot be proven, the runner replaces the outward failure with typed `no_go_artifact_binding`, preserves the cleanup diagnostic, writes one terminal receipt, and grants no independent terminal-verification or downstream authority. It does not retry cleanup through another path, delete unowned content, or leave a started-only attempt.

## Risks / Trade-offs

- [A legitimate report is accidentally excluded] -> Use two exact, lowercase readiness namespaces and add lookalike-path negative regressions; do not exclude generic `candidate_seed_inventory.json.gz` basenames.
- [Producer and verifier classifiers drift] -> Keep a shared fixture table in tests while retaining separate production implementations.
- [Cleanup deletes a path not created by this invocation] -> Require an in-memory ownership flag plus exact derived-path equality; pre-existing-path tests prove preservation.
- [Cleanup failure masks the original gate] -> Preserve the original diagnostic as context but type the terminal decision as `artifact_binding`, because independently reviewable artifact closure failed.
- [The next candidate still approaches the ceiling] -> Preserve all ceilings and use source-only size/binding tests; any later attempt requires a separately preregistered source and cannot tune limits in place.

## Migration Plan

1. Add RED path-classification and failure-cleanup regressions, including producer/verifier parity and unowned-path preservation.
2. Implement the two exact source exclusions independently in the seed helper and readiness verifier.
3. Implement ownership-scoped staging cleanup in the readiness runner and cover ceiling, verifier, and cleanup-failure branches.
4. Run focused source-only suites, strict OpenSpec validation, independent review, and the repository commit gate once.
5. Sync, archive, commit, and push the repair without creating or invoking r4.

Before a later readiness attempt is proposed, rollback is an ordinary revert of this source-only repair. The consumed r3 evidence remains immutable under either outcome.

## Open Questions

None. A later change must separately decide whether a new readiness identity is warranted after this repair is pushed.
