## Why

The Windows production test environment now needs about 33 minutes to run the full pytest suite, while a representative coordinator-focused gate completes in under one second. Requiring the full suite at every coherent commit is becoming an iteration bottleneck, so the repository needs a bounded, explicit commit gate without weakening the full validation boundary.

## What Changes

- Add a repository-owned test-gate runner with named `commit`, `protocol`, `gameplay`, `noncombat-evidence`, and `full` profiles.
- Define profiles in a validated JSON manifest that is compatible with the current Python 3.10 runtime and introduces no new dependency.
- Make `commit` include the default test set except for a small, measured `full_only` list, so newly added tests run by default rather than being silently omitted.
- Document which change classes require a focused profile, the commit gate, or the full suite.
- Record profile test counts and wall-clock duration, propagate pytest failures unchanged, and fail closed when the manifest or a target is invalid.
- Keep the full suite as the merge, release, broad-refactor, and shared-test-infrastructure gate.

Non-goals are installing Git hooks, adding a remote CI requirement, retrying flaky tests, changing gameplay behavior, installing `pytest-xdist`, or removing any test from the full suite.

## Capabilities

### New Capabilities

- `tiered-pytest-gates`: Explicit, validated pytest profiles for fast commit feedback and unchanged full-suite validation.

### Modified Capabilities

None.

## Impact

- Adds a small Python runner under `scripts/`, a JSON manifest and runner tests under `tests/`, and repository testing documentation.
- Uses `sys.executable`, pytest's existing `no:cacheprovider` workaround, and a repository-local base temporary directory.
- The measured baseline is `3455 passed, 1 timing-sensitive failure in 33:34`; that failed evidence-runner test passed alone in 3.08 seconds. The initial success metric is a repeatable `commit` profile at or below five minutes on `D:\anaconda\envs\stsai\python.exe`.
- The rollback boundary is limited to the new runner, manifest, tests, and documentation; existing pytest invocation and test files remain valid independently.
