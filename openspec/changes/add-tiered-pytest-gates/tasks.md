## 1. Regression Coverage

- [x] 1.1 Add failing tests for manifest schema validation, missing targets, empty profiles, and whole-file `full_only` enforcement.
- [x] 1.2 Add failing tests for profile command construction, current-interpreter use, repository-local `basetemp`, list and dry-run output, elapsed-time reporting, and pytest exit-code propagation.

## 2. Gate Runner

- [x] 2.1 Add the versioned JSON manifest with `commit`, `protocol`, `gameplay`, `noncombat-evidence`, and `full` profile definitions.
- [x] 2.2 Implement manifest loading and fail-closed validation in `scripts/run_test_gate.py`.
- [x] 2.3 Implement serial pytest command construction and execution with `no:cacheprovider`, profile-local `basetemp`, command reporting, duration reporting, and unchanged pytest exit status.
- [x] 2.4 Implement `--list` and `--dry-run` without launching pytest.

## 3. Qualification And Documentation

- [x] 3.1 Measure candidate heavy files, keep `full_only` whole-file and minimal, and record a rationale for every exclusion.
- [x] 3.2 Run each positive profile and adjust targets until they collect nonzero tests and remain useful for their named domain.
- [x] 3.3 Qualify the `commit` profile at no more than five minutes on `D:\anaconda\envs\stsai\python.exe` and write a dated qualification report with counts, exclusions, result, and duration.
- [x] 3.4 Document runner commands, profile purposes, the focused/commit/full trigger matrix, and rollback behavior.

## 4. Verification

- [x] 4.1 Run the runner-focused regression tests and all named profiles.
- [x] 4.2 Run the unchanged `full` profile once and record any timing-sensitive failure separately rather than retrying it inside the runner.
- [x] 4.3 Validate the OpenSpec change and confirm every requirement has corresponding test or qualification evidence.
