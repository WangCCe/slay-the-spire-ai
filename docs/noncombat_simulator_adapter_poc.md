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

The original registered 2026-08-02 adapter-only fit report binds:

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

The later bounded-training integration found and repaired shared-map clone
ownership and undefined snapshot fields. Its replacement `r2` fit binds adapter
commit `68369db646a074fa712fccddc6a650015197332d`, adapter source SHA-256
`933f7725cc7cb3dfd088e26bd2c81856e09bacac24c6f1e1e98246db62cabb41`,
and native module SHA-256
`d4055640698ca415ea5f4d57e11ac5fd4635143039bfefd869c60ddf64924b3c`.
The simulator commit and physical-source identity are unchanged. The original
fit remains historical evidence; `r2` is the fit consumed by the smoke.

The policy-validity extension adds the read-only native target policy
`sts_lightspeed_simple_agent_target_v1` under adapter API v2. Its `r3` fit binds
adapter commit `a810d6d0ce92c1ebab8483fb8819163fc76d54fe`, adapter source SHA-256
`10c413d11e6abf4c621400279a4f4bfccddb0876426a0e14c6c892fdf0d4da5b`,
and native module SHA-256
`b3328aea4ee3040a4fe8751d6f300a148a7ae64d68f7ebec050ae61f479d6805`.
The fit checked 770 native target decisions across seeds `0..19` twice,
covered all four categories, matched one current candidate per query, preserved
source bytes, reached terminal outcomes, and retained 12/12 historical-prefix
matches. The simulator physical-source identity remains unchanged and dirty by
explicit registration.

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

The bounded simulator-training smoke and its separately registered policy
validity study are complete. Their contracts, results, limitations, and next
boundary are documented in `docs/noncombat_simulator_training_smoke.md` and
`docs/noncombat_simulator_policy_validity.md`. The trained smoke ranker beat its
seeded initialization but lost to native SimpleAgent on the fresh validity
cohort. Neither result grants formal-training or live authority.
