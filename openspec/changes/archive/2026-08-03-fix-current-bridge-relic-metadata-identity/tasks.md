## 1. Planning And Red Evidence

- [x] 1.1 Strict-validate the change, recheck the clean upstream Cards/Relics
  source and frozen metadata identities, then commit and push planning artifacts
  before changing bridge code or tests.
- [x] 1.2 Add red parametrized regressions for all 15 aliases, both metadata
  exemptions, exact direct matching, mapped-ID direct-name bypass, unknown IDs,
  missing alias targets, wrong exemption names, and shop non-mutation behavior.
- [x] 1.3 Write a durable offline item identity audit with exact source hashes,
  card coverage, relic counts, the complete 15-pair alias table, both fallback
  relic call sites, and the no-execution authority boundary.

## 2. Narrow Relic Identity Repair

- [x] 2.1 Add one closed 17-entry stable-ID table containing each expected
  native name and either its canonical metadata name or an explicit `None` only
  for `CIRCLET` and `RED_CIRCLET`.
- [x] 2.2 Change only the relic metadata lookup branch to validate listed IDs
  before direct lookup, canonicalize aliases, allow the two exact exemptions,
  and preserve ID, slot, counter, price, exact-name behavior, source bytes, and
  existing structural blockers.
- [x] 2.3 Run the red regressions to green and review the diff for generic name
  normalization, card/potion changes, adapter changes, diagnostic changes, or
  unrelated policy behavior.

## 3. Verification And Closeout

- [x] 3.1 Run focused bridge, adapter, relic heuristic, and adjacent hydration
  pytest with a fresh writable basetemp, `py_compile`, `git diff --check`, and
  strict change plus global OpenSpec validation.
- [x] 3.2 Run the partitioned repository `commit` test gate instead of a raw
  unregistered full pytest suite, and confirm no native environment, seed,
  gameplay, model, reward, OPE, formal-RL, training, qualification, loading, or
  promotion surface was touched.
- [x] 3.3 Update project direction, sync the delta requirement, archive the
  completed change, commit the cohesive repair, and push `master` while
  preserving unrelated local artifacts.
