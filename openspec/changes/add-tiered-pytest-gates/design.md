## Context

The repository's default pytest suite contains 3,456 tests and took 33:34 in the measured Windows production environment. The slowest observed tests are subprocess and Git-replay checks in the non-combat outcome-evidence runner and verifier, with individual calls taking roughly 7-12 seconds. In contrast, the 32 coordinator and startup tests used for the latest protocol fix completed in 0.70 seconds.

The repository currently has no pytest markers, test-tier runner, CI gate, or documented trigger matrix. Development must continue to use `D:\anaconda\envs\stsai\python.exe`, disable the pytest cache provider, and place `basetemp` under the writable repository root.

## Goals / Non-Goals

**Goals:**

- Provide one explicit repository command for repeatable named test profiles.
- Keep the routine `commit` profile at or below five minutes in the designated Windows environment.
- Include new tests in `commit` by default unless they are deliberately classified as `full_only`.
- Preserve the complete pytest suite as the final validation boundary.
- Fail closed on invalid configuration and expose enough command, count, duration, and exit information to audit each run.

**Non-Goals:**

- Installing Git hooks or adding a remote CI requirement.
- Adding `pytest-xdist`, automatic retries, or a new package dependency.
- Inferring tests automatically from Git diffs or Python imports.
- Changing, deleting, weakening, or skipping tests in the `full` profile.
- Changing gameplay, CommunicationMod configuration, training, or RL behavior.

## Decisions

### Use a standard-library runner and JSON manifest

`scripts/run_test_gate.py` will load `tests/test_gate_manifest.json`, validate it, construct a pytest command using `sys.executable -m pytest`, and return pytest's exit code. JSON is used because the production runtime is Python 3.10 and can parse it without an added TOML dependency.

The runner will support named profiles, `--list`, and `--dry-run`. It will always add `-p no:cacheprovider` and a profile-specific repository-local `--basetemp` unless the invocation is dry-run only.

Alternatives considered were pytest markers and Git-diff inference. Markers require broad churn and are easy to omit on new tests; diff inference has a larger false-negative surface than this first change should own.

### Define commit by exclusion, domain profiles by inclusion

The `commit` profile will start from the repository's configured test paths and exclude only manifest entries in `full_only`. This makes newly added tests part of routine validation by default. The initial `full_only` list will be selected from measured subprocess/Git replay costs and tuned until `commit` is at or below five minutes.

The `protocol`, `gameplay`, and `noncombat-evidence` profiles will be explicit positive target lists. They are focused development tools, not substitutes for `commit` or `full`.

The `full` profile will invoke the existing configured test paths without the `full_only` exclusions. The manifest cannot redefine the full test universe.

### Validate configuration before launching pytest

The runner will reject an unsupported schema version, unknown keys, missing or duplicate profile names, malformed target lists, nonexistent file targets, empty positive profiles, and a `full_only` entry outside the configured test paths. A manifest error exits before pytest with a distinct command-usage failure code.

Node IDs are allowed for positive profiles but `full_only` entries must be whole files. Whole-file exclusions keep `commit` behavior visible and prevent hidden partial exclusion inside large test files.

### Preserve failures and report evidence

The runner will print the selected profile and resolved pytest command before execution, then report the wall-clock duration and exit code. Pytest failures, collection errors, and interruptions are returned unchanged. The runner will not retry a failure or reinterpret a flaky result as success.

### Use an explicit trigger matrix

- During red-green iteration, run the narrowest relevant pytest node or named domain profile.
- Before each coherent code or test commit, run `commit`.
- Run `full` when changing pytest configuration, shared test infrastructure, the gate runner or manifest, any `full_only` test, broad cross-domain code, or at merge/release/phase-close boundaries.
- Documentation-only changes do not require pytest unless they change executable examples or the manifest.

The trigger matrix will be documented beside the command examples. It remains a human/Codex decision in this version; no hook will inspect Git state automatically.

## Risks / Trade-offs

- [Risk] `full_only` grows until routine validation becomes weak. -> Mitigation: require a measured reason and description for every exclusion, test that each entry exists, and keep the list intentionally small.
- [Risk] A newly added slow test makes `commit` exceed five minutes. -> Mitigation: new tests remain included by default; a measured follow-up can classify a whole file as `full_only` without hiding the regression.
- [Risk] Domain profiles drift from source ownership. -> Mitigation: profile targets are validated and documented as focused tools; `commit` remains the default pre-commit gate.
- [Risk] Parallelization could introduce filesystem or subprocess flakes. -> Mitigation: keep the first implementation serial and evaluate `pytest-xdist` separately only after isolation evidence exists.
- [Trade-off] The complete suite remains slow. -> This change optimizes the routine feedback loop first; it does not claim to solve full-suite runtime.

## Migration Plan

1. Add runner regression tests that fail before the runner and manifest exist.
2. Implement manifest validation, command construction, reporting, and profile execution.
3. Measure candidate `commit` profiles on the production Windows Python and record the final `full_only` rationale.
4. Run runner-focused tests, every named profile, the measured `commit` gate, and one unchanged `full` validation.
5. Document commands and the trigger matrix, then use `commit` for subsequent routine changes.

Rollback removes the new runner, manifest, tests, and documentation. Direct pytest commands continue to work throughout the migration.

## Open Questions

None. The first version is intentionally serial and manually invoked.
