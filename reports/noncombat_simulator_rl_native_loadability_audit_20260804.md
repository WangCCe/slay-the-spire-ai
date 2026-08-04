# Non-Combat Simulator RL Native Loadability Audit

Date: 2026-08-04

## Scope

This is a read-only audit of the terminal
`noncombat-simulator-rl-20260804-r1` startup failure. It does not alter the
terminal artifact set, load an environment, access a registered seed, train,
start Slay the Spire, or contact Communication Mod.

The immutable terminal manifest SHA-256 is
`01fe28cd35c13dcdee305189a27488474edfebfb126ba79aa145ab56d08c8080`.
The result remains `experiment_blocked`, with zero episodes and zero optimizer
updates.

## Finding

The bound `.pyd` is loadable in the registered Python 3.10.18 runtime. The
failure is process-global DLL resolution caused by import order. The runner's
top-level experiment import reached `noncombat_policy_model`, which imported
PyTorch; source-only preflight also imported PyTorch to read its version. Both
paths ran before native loading:

1. Importing PyTorch 2.5.1 first loads Conda's 2016 MinGW runtime DLLs from
   `D:/anaconda/envs/stsai/Library/mingw-w64/bin`.
2. The adapter then loads CLion's GCC 15.2.0 `libstdc++-6.dll`.
3. Windows reuses the already-loaded DLL named `libwinpthread-1.dll` instead of
   loading the CLion copy from the supplied DLL directory.
4. CLion's `libstdc++-6.dll` imports `clock_gettime64` and `nanosleep64`; the
   Conda DLL exports neither symbol. Windows therefore returns error 127,
   reported by Python as `DLL load failed ... The specified procedure could not
   be found`.

The direct import table of the `.pyd` matches every export in the intended
Python, Windows, and CLion dependencies. The missing procedures appear only
when the intended CLion `libstdc++-6.dll` is paired with the already-loaded
Conda `libwinpthread-1.dll`.

## Reproduction Matrix

| Fresh-process sequence | Result |
|---|---|
| Load the three CLion MinGW runtime DLLs independently | Pass |
| Load the bound `.pyd` before importing PyTorch | Pass |
| Import PyTorch, then load the bound `.pyd` | Fail with WinError 127 |
| Load the bound `.pyd`, then initialize PyTorch and `CandidateRanker` | Pass |

Module inspection confirmed the effective paths:

- Torch-first: Conda `libgcc_s_seh-1.dll` and `libwinpthread-1.dll`.
- Native-first: CLion `libgcc_s_seh-1.dll`, `libstdc++-6.dll`, and
  `libwinpthread-1.dll`; PyTorch subsequently initializes successfully.

Relevant runtime identities:

| File | Size | SHA-256 |
|---|---:|---|
| Conda `libwinpthread-1.dll` | 56,978 | `6f6359c0fda76adceb781d3797a982cb3bb5f491a1ed206afa00c63681236bd2` |
| CLion `libwinpthread-1.dll` | 72,032 | `806597c6b97584ed219bd127f0678a5ee6ad5977191a3a996463a3a42ebe206a` |
| Conda `libgcc_s_seh-1.dll` | 83,230 | `58bff7edc7864c52560c2db731b3e864f37fa352f0234e4887bb4d7c9ce1e2c6` |
| CLion `libgcc_s_seh-1.dll` | 937,624 | `ea8f5bb64e1c162b1552ce57d093697f7cf0b155ed40c0908668be7139b60b66` |
| CLion `libstdc++-6.dll` | 26,876,280 | `14fb0a5a7e14c6d43883764cc5cca3c0174790d1e1fc9d6d740f58b3b8fa38dc` |

## Attempt-Boundary Assessment

The one-logical-execution rule remains appropriate after empirical execution
starts. It prevents selection by retry, seed replacement, threshold changes,
or post-result tuning.

The current boundary is too early. It writes the started journal before proving
that the bound native module and PyTorch can coexist in the execution process.
A startup compatibility failure consumes the logical execution despite
constructing no environment and accessing no seed. That adds no experimental
integrity and makes infrastructure repair unnecessarily expensive.

For future executions, native load, provenance validation, and pristine CPU
training-runtime initialization should complete before output initialization
and the started journal. A failure in this pre-start phase should leave output
absent and should not count as an experiment attempt. Once the started journal
exists, the existing checkpoint, resume, no-retry, cohort, and authority rules
remain unchanged.

The archived r1 result is not retroactively changed or retried. A future
experiment still requires a separate source commit, registration,
authorization, logical execution id, and explicit cohort decision.

## Recommended Source Fix

1. Load and validate the bound native module before any call that imports or
   initializes PyTorch.
2. Initialize the pristine CPU training runtime before creating a fresh output
   directory or started journal.
3. For a resume, load native before restoring Torch state; a pre-rollout load or
   restore failure must preserve the last journal/checkpoint rather than append
   a new terminal result.
4. Add regressions for ordering, absent-output startup failure, reusable
   pre-start authorization, unchanged resume evidence, and post-start terminal
   failure.
5. Keep the archived r1 artifacts byte-identical and grant no successor
   execution, seed, training, live, qualification, loading, or promotion
   authority from this repair.

A separate static-link POC was not used as evidence because the constrained
CMake compiler-ABI probe did not complete within its bounded diagnostic window.
The import-order root cause and native-first remedy were both demonstrated
directly in fresh processes.
