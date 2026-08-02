# Non-Combat Simulator Adapter POC

## Scope

This POC provides an optional, offline adapter from this repository to a local
`sts_lightspeed` checkout. It supports deterministic reset, clone, canonical
snapshot, legal-action enumeration, transition stepping, and terminal outcome
reporting for route, shop, event, and card-reward decisions.

It is not loaded by the live gameplay runtime and does not authorize gameplay,
training, OPE reinterpretation, qualification, study launch, or promotion.
Simulator transitions use `noncombat-simulator-transition-v1` and cannot enter
the live known-propensity or supported-outcome evidence sets.

## Bound Source Identity

The registered 2026-08-02 fit report binds:

- adapter commit `dbf67c01cd30c16d4eb2a6d9b45a1d9816898cbe`
- adapter source SHA-256
  `300a8e18d49a089c42d75f8b1f5858f970d49f97ae8a92bdb284422ca4e5d463`
- simulator commit `7476a81954020087da31d41d16fddf475746ec2d`
- physical simulator source SHA-256
  `a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a`
- `json` submodule `55f93686c01528224f448c19128836e7df245f72`
- `pybind11` submodule `8f68ecd32c8e18d3b064dbf0ea5fc31a6cb37e9a`
- native module SHA-256
  `a919d449b6f73e47e8a79e70f0db09ebaa18287c08a658a799e4ac1adf6c9274`

The simulator checkout was dirty, so the physical-source hash, not the parent
commit alone, is the binding identity.

## Reproducible Build

Run from the repository root in PowerShell. The build stays out of both source
trees and the output directory is ignored by Git.

```powershell
& 'D:\programs\CLion\bin\cmake\win\x64\bin\cmake.exe' `
  -S simulator_adapters\sts_lightspeed `
  -B .sts_lightspeed_adapter_build `
  -G Ninja `
  -DSTS_LIGHTSPEED_ROOT='D:\CLionProjects\sts_lightspeed' `
  -DCMAKE_MAKE_PROGRAM='D:\programs\CLion\bin\ninja\win\x64\ninja.exe' `
  -DCMAKE_CXX_COMPILER='D:\programs\CLion\bin\mingw\bin\g++.exe' `
  -DPython_EXECUTABLE='D:\anaconda\envs\stsai\python.exe' `
  -DPython_ROOT_DIR='D:\anaconda\envs\stsai' `
  -DCMAKE_BUILD_TYPE=Release

& 'D:\programs\CLion\bin\cmake\win\x64\bin\cmake.exe' `
  --build .sts_lightspeed_adapter_build `
  --target sts_lightspeed_noncombat_adapter
```

The registered build used Python 3.10.18, GCC 15.2.0, C++17, and pybind11
3.0.2a0. The native adapter intentionally disables the upstream SimpleAgent's
battle-potion use and restores carried potions after each baseline-controlled
combat. This avoids an upstream invalid-potion-enum read and is part of the
declared baseline identity `sts_lightspeed_simple_agent_no_potions_v1`.

## Fit Audit

```powershell
& 'D:\anaconda\envs\stsai\python.exe' `
  -m analysis_scripts.noncombat_simulator_fit `
  --input reports\noncombat_simulator_fit_20260802_input.json `
  --simulator-repo 'D:\CLionProjects\sts_lightspeed' `
  --module .sts_lightspeed_adapter_build\sts_lightspeed_noncombat_adapter.cp310-win_amd64.pyd `
  --dll-directory 'D:\programs\CLion\bin\mingw\bin' `
  --runs-directory 'D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD' `
  --json-output reports\noncombat_simulator_fit_20260802.json `
  --markdown-output reports\noncombat_simulator_fit_20260802.md
```

The report verdict is `adapter_poc_ready`:

- two 20-seed batches produced identical summaries;
- all 20 seeds reached terminal states;
- route, shop, event, and card-reward decisions were observed;
- all 46 inspected candidates were legal on isolated clones;
- 12/12 historical early reward candidate sets matched across six real runs;
- the first-candidate baseline won 0/20 runs; and
- every authority flag is false.

## Evidence Boundary

The POC does not prove full mechanics equivalence or useful policy quality.
Neow, boss relics, campfires, treasure, follow-up card selections, and combat
remain baseline-controlled. Historical agreement covers only twelve early
candidate sets, and the upstream loader cannot import arbitrary live
non-combat states.

A separately reviewed OpenSpec change is required before any simulator-training
smoke. That change must preserve the simulated/live evidence boundary and
define fixed train/holdout seeds, a training-only reward contract, divergence
checks, resource bounds, promotion exclusions, and stop conditions.
