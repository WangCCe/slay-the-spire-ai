## 1. Contract And Regressions

- [x] 1.1 Add RED runner tests for schema version 2, `commit_deselect` validation, duplicate/invalid entries, and exact repository manifest content.
- [x] 1.2 Add RED command tests proving only `commit` emits node deselections while `full` and focused profiles remain inclusive.

## 2. Runner And Boundary

- [x] 2.1 Implement fail-closed node-level manifest parsing and commit command construction without changing direct pytest or other profiles.
- [x] 2.2 Add the frozen 21-node measured boundary from `pytest_gate_commit_profile_20260828_r2.json` and preserve all containing files in routine collection.
- [x] 2.3 Update testing documentation with ownership, focused-validation, rollback, and raw-full boundary rules.

## 3. Qualification

- [x] 3.1 Run runner-focused pytest and strict validation for this change and the complete OpenSpec tree.
- [x] 3.2 Freeze the boundary, commit and push it, then run one timing-enabled `commit` qualification without retry; require zero failures and at most 240 runner seconds.
- [x] 3.3 Prove the unchanged inclusive `full` argv through runner regressions and a repository-manifest dry-run; do not repeat the known 2,868-second failing raw-full baseline solely for commit-only selection equivalence.
- [x] 3.4 Record timing and complete-boundary evidence, sync the accepted delta spec, archive the change, and push the final documentation commit.
