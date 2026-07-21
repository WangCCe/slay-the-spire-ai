# Tiered Pytest Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit, fail-closed pytest profiles that keep routine commit validation below five minutes while preserving the unchanged full suite.

**Architecture:** A standard-library Python runner loads a versioned JSON manifest, validates all profiles and targets, and launches pytest with the current interpreter and a repository-local base temporary directory. `commit` starts from pytest's configured test paths and excludes only measured whole-file `full_only` entries; domain profiles use explicit positive targets, and `full` applies no exclusions.

**Tech Stack:** Python 3.10 standard library, pytest 9.0.2, JSON, OpenSpec.

## Global Constraints

- Use `D:\anaconda\envs\stsai\python.exe` for qualification and full validation.
- Add no package dependency, Git hook, remote CI requirement, retry behavior, or `pytest-xdist` configuration.
- Keep `full_only` whole-file, measured, documented, and intentionally small.
- Newly added tests under configured pytest paths must enter `commit` by default.
- Preserve pytest's nonzero exit code and never reinterpret a flaky result as success.
- Use `-p no:cacheprovider --basetemp <repository-local path>` for Windows pytest commands.
- Do not change gameplay, CommunicationMod configuration, training, or RL behavior.

---

### Task 1: Manifest Contract And Validation

**Files:**
- Create: `tests/test_run_test_gate.py`
- Create: `tests/test_gate_manifest.json`
- Create: `scripts/run_test_gate.py`

**Interfaces:**
- Produces: `ManifestError(ValueError)` for fail-closed configuration errors.
- Produces: `FullOnlyTarget(path: str, reason: str)`, `TestProfile(description: str, mode: str, targets: tuple[str, ...])`, and `TestGateManifest(schema_version: int, full_only: tuple[FullOnlyTarget, ...], profiles: dict[str, TestProfile])`.
- Produces: `load_manifest(path: Path, repo_root: Path) -> TestGateManifest`.
- Produces: `_configured_test_paths(repo_root: Path) -> tuple[Path, ...]`.

- [ ] **Step 1: Write failing manifest tests**

Create a temporary repository fixture containing `pytest.ini`, a `tests/` directory, and small test files. Cover one valid manifest and these invalid cases: duplicate JSON key, unsupported schema version, unknown top-level/profile key, missing required profile, malformed list, blank description or rationale, duplicate target, nonexistent file, empty positive profile, node ID in `full_only`, and `full_only` outside configured test paths.

Use the actual manifest shape in the tests:

```python
VALID_MANIFEST = {
    "schema_version": 1,
    "full_only": [
        {"path": "tests/test_slow.py", "reason": "measured subprocess replay"}
    ],
    "profiles": {
        "commit": {
            "description": "routine pre-commit validation",
            "mode": "default-minus-full-only",
            "targets": [],
        },
        "protocol": {
            "description": "communication protocol validation",
            "mode": "targets",
            "targets": ["tests/test_fast.py::test_fast"],
        },
        "gameplay": {
            "description": "gameplay policy validation",
            "mode": "targets",
            "targets": ["tests/test_fast.py"],
        },
        "noncombat-evidence": {
            "description": "non-combat evidence validation",
            "mode": "targets",
            "targets": ["tests/test_fast.py"],
        },
        "full": {
            "description": "complete repository validation",
            "mode": "default",
            "targets": [],
        },
    },
}
```

- [ ] **Step 2: Run the manifest tests and verify RED**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_test_gate_red tests/test_run_test_gate.py
```

Expected: collection fails because `scripts.run_test_gate` does not exist.

- [ ] **Step 3: Implement duplicate-aware JSON loading and manifest validation**

Implement duplicate detection with `json.loads(..., object_pairs_hook=_reject_duplicate_keys)`. Parse `pytest.ini` with `configparser.ConfigParser`, resolve configured test paths under `repo_root`, and reject targets whose file portion does not exist. Require the five named profiles; require `commit.mode == "default-minus-full-only"`, `full.mode == "default"`, and domain modes to equal `"targets"`.

The target validator must split node IDs only for positive profiles:

```python
def _target_file(target: str) -> str:
    return target.split("::", 1)[0]


def _is_under_test_paths(path: Path, test_paths: tuple[Path, ...]) -> bool:
    for test_path in test_paths:
        if test_path.is_file() and path == test_path:
            return True
        if test_path.is_dir() and path.is_relative_to(test_path):
            return True
    return False
```

- [ ] **Step 4: Add the initial repository manifest**

Define the five required profiles. Start `full_only` with the two files identified by the 2026-07-20 duration run:

```json
[
  {
    "path": "tests/test_noncombat_outcome_evidence_runner.py",
    "reason": "subprocess, crash-recovery, and temporary Git replay matrix"
  },
  {
    "path": "tests/test_noncombat_outcome_evidence_verifier.py",
    "reason": "independent verifier subprocess and historical Git replay matrix"
  }
]
```

Use explicit targets for `protocol`, `gameplay`, and `noncombat-evidence`; do not add a test to `full_only` without measured evidence.

The initial positive targets are:

```json
{
  "protocol": [
    "tests/test_deferred_state_callback.py",
    "tests/test_coordinator_startup_timeout.py",
    "tests/test_main_runtime_errors.py",
    "tests/test_startup.py",
    "tests/test_card_select_confirm_guard.py",
    "tests/test_combat_reward_action_guards.py"
  ],
  "gameplay": [
    "tests/test_map_routing_safety.py",
    "tests/test_shop_screen_guards.py",
    "tests/test_event_choice_guard.py",
    "tests/test_ironclad_card_reward_guards.py",
    "tests/test_rest_guard.py",
    "tests/test_decision_context_guards.py",
    "tests/test_offline_decision_comparator.py"
  ],
  "noncombat-evidence": [
    "tests/test_noncombat_exploration.py",
    "tests/test_noncombat_exploration_adapters.py",
    "tests/test_noncombat_exploration_evidence.py",
    "tests/test_noncombat_exploration_persistence.py",
    "tests/test_noncombat_exploration_runtime.py",
    "tests/test_noncombat_rl_decision_loop.py",
    "tests/test_noncombat_ope_readiness.py",
    "tests/test_noncombat_ope_estimation.py",
    "tests/test_noncombat_ope_calibration.py",
    "tests/test_noncombat_ope_influence.py",
    "tests/test_noncombat_ope_estimate_artifacts.py",
    "tests/test_noncombat_ope_artifact_verifier.py",
    "tests/test_noncombat_ope_bootstrap.py",
    "tests/test_noncombat_outcome_evidence_gate.py",
    "tests/test_noncombat_outcome_evidence_pool.py",
    "tests/test_noncombat_outcome_evidence_finalizer.py",
    "tests/test_noncombat_outcome_evidence_expansion.py"
  ]
}
```

- [ ] **Step 5: Run the manifest tests and verify GREEN**

Run the same focused pytest command. Expected: every manifest validation test passes.

- [ ] **Step 6: Commit the manifest contract**

```powershell
git add scripts/run_test_gate.py tests/test_run_test_gate.py tests/test_gate_manifest.json
git commit -m "test: define tiered pytest gate manifest"
```

### Task 2: Command Construction And Runner Behavior

**Files:**
- Modify: `scripts/run_test_gate.py`
- Modify: `tests/test_run_test_gate.py`

**Interfaces:**
- Consumes: `TestGateManifest` and its validated profiles from Task 1.
- Produces: `build_pytest_command(profile_name: str, manifest: TestGateManifest, repo_root: Path, basetemp_root: Path) -> list[str]`.
- Produces: `run_profile(profile_name: str, manifest_path: Path, repo_root: Path, dry_run: bool = False, executor: Callable[..., CompletedProcess] = subprocess.run, clock: Callable[[], float] = time.perf_counter) -> int`.
- Produces: `main(argv: Sequence[str] | None = None) -> int` with `--list`, `--dry-run`, and an optional profile positional argument.

- [ ] **Step 1: Write failing command and execution tests**

Add tests asserting:

- the command starts with `[sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"]`;
- every profile gets `--basetemp <repo>/.pytest_gates/<profile>`;
- `commit` emits one `--ignore=<path>` per `full_only` file and no positive targets;
- `full` emits no ignore or positive target;
- domain profiles append their configured targets;
- `--list` prints profile names and descriptions without calling the executor;
- `--dry-run` prints the Windows-safe command without calling the executor;
- a fake executor return code `7` is returned unchanged;
- a fake clock sequence `[10.0, 12.5]` produces a `2.50s` elapsed report;
- manifest errors return `2` and do not call the executor.

- [ ] **Step 2: Run the new tests and verify RED**

Run the focused test file. Expected: failures identify the missing command builder and runner behavior.

- [ ] **Step 3: Implement deterministic command construction**

Build commands as argument lists. Use `subprocess.list2cmdline(command)` only for display; pass the original list to `subprocess.run(command, cwd=repo_root, check=False)`. Render commit exclusions as repository-relative `--ignore=tests/<file>.py` arguments and profile targets as repository-relative strings.

- [ ] **Step 4: Implement CLI, reporting, and exit propagation**

`main()` must return `2` after printing `test gate configuration error: <message>` to stderr for `ManifestError`. It must not catch or rewrite pytest's return code. The module entrypoint is:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Run runner tests and profile dry-runs**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_test_gate_green tests/test_run_test_gate.py
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py --list
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit --dry-run
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py full --dry-run
```

Expected: tests pass, all five profiles list, commit shows only documented ignores, and full shows no ignores.

- [ ] **Step 6: Commit executable runner behavior**

```powershell
git add scripts/run_test_gate.py tests/test_run_test_gate.py
git commit -m "test: add explicit pytest gate runner"
```

### Task 3: Profile Qualification And Trigger Documentation

**Files:**
- Modify: `tests/test_gate_manifest.json`
- Create: `reports/pytest_gate_qualification_20260721.md`
- Create: `docs/testing.md`
- Modify: `openspec/changes/add-tiered-pytest-gates/tasks.md`

**Interfaces:**
- Consumes: the runner CLI from Task 2.
- Produces: a dated qualification report with baseline, final profile membership, counts, duration, and result.
- Produces: a stable user workflow documented in `docs/testing.md`.

- [ ] **Step 1: Run each positive profile**

Run `protocol`, `gameplay`, and `noncombat-evidence` with the production Windows Python. Every profile must collect at least one test and pass. Adjust only positive target lists when a profile is semantically incomplete or too broad for focused iteration.

- [ ] **Step 2: Measure the initial commit profile**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py commit
```

Record pytest's passed/failed count and the runner's elapsed duration. If duration exceeds five minutes, rerun candidate heavy files separately with `--durations=25 --durations-min=0.25`; add a whole file to `full_only` only when its measured cost is material and its rationale is recorded.

- [ ] **Step 3: Write the qualification report**

`reports/pytest_gate_qualification_20260721.md` must contain:

- full baseline: 3,456 tests, `33:34`, and the one timing-sensitive evidence-runner failure that passed alone;
- focused baseline: 32 coordinator/startup tests in `0.70s`;
- final `full_only` entries with measured rationale;
- each named profile's collected/pass count and duration;
- final commit result and explicit comparison to the five-minute threshold;
- statement that no test is removed from `full` and no gameplay run is required.

- [ ] **Step 4: Document the trigger matrix**

Create `docs/testing.md` with exact Windows commands and this table:

| Change class | Required validation |
|---|---|
| Red-green iteration | Narrow node or relevant domain profile |
| Coherent code/test commit | Relevant focused tests, then `commit` |
| Pytest config, shared fixture, gate runner/manifest, or `full_only` test | `full` |
| Broad cross-domain refactor, merge, release, or phase close | `full` |
| Documentation only | No pytest unless executable examples or manifest change |

State that failures are never retried by the runner and that direct pytest remains the rollback path.

- [ ] **Step 5: Run the unchanged full profile once**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe scripts\run_test_gate.py full
```

Expected: the runner applies no `full_only` exclusions. Record the exact result; if the known stream-silence test flakes again, report it and rerun only that node for diagnosis, without changing the runner result.

- [ ] **Step 6: Validate artifacts and close OpenSpec tasks**

Run:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_test_gate_final tests/test_run_test_gate.py
openspec validate add-tiered-pytest-gates
git diff --check
```

Mark each completed checkbox in `openspec/changes/add-tiered-pytest-gates/tasks.md`. Expected: runner tests pass, OpenSpec validates, and diff check reports no whitespace errors.

- [ ] **Step 7: Commit qualification and documentation**

```powershell
git add tests/test_gate_manifest.json reports/pytest_gate_qualification_20260721.md docs/testing.md openspec/changes/add-tiered-pytest-gates/tasks.md
git commit -m "docs: qualify tiered pytest gates"
```

### Task 4: Final Review And Publication

**Files:**
- Review: `scripts/run_test_gate.py`
- Review: `tests/test_run_test_gate.py`
- Review: `tests/test_gate_manifest.json`
- Review: `docs/testing.md`
- Review: `reports/pytest_gate_qualification_20260721.md`
- Review: `openspec/changes/add-tiered-pytest-gates/`

**Interfaces:**
- Consumes: all deliverables from Tasks 1-3.
- Produces: a pushed branch with a validated OpenSpec change and reproducible gate evidence.

- [ ] **Step 1: Review spec coverage and repository status**

Map every requirement in `specs/tiered-pytest-gates/spec.md` to a runner test, profile run, report row, or documentation section. Confirm unrelated untracked reports remain untouched.

- [ ] **Step 2: Push the branch**

```powershell
git push
```

Expected: `codex/noncombat-ope-readiness` is synchronized with its remote. Do not archive the OpenSpec change until the user confirms the implementation.
