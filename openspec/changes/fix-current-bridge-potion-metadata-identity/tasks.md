## 1. Planning And Red Evidence

- [x] 1.1 Strict-validate the change, review the r2 closeout and exact upstream
  and metadata identities, then commit and push all planning artifacts before
  editing bridge code or tests.
- [ ] 1.2 Add red focused regressions for all three registered aliases, mapped
  IDs with unexpected names, unknown IDs, missing canonical metadata, direct
  exact-name compatibility, and shop source-slot/price/non-mutation behavior.
- [ ] 1.3 Write a durable offline audit report that separates the observed r2
  `Elixir Potion` failure from the two additional static compatibility findings
  and records that the other 40 native names match metadata.

## 2. Narrow Compatibility Repair

- [ ] 2.1 Add one closed stable-ID mapping containing the exact expected native
  and canonical metadata names for `ELIXIR_POTION`, `FAIRY_POTION`, and
  `GAMBLERS_BREW`.
- [ ] 2.2 Change only the failed potion metadata lookup branch to require both
  sides of a registered mapping, hydrate aliases with the canonical metadata
  name, and preserve native ID, source slot, price, source bytes, exact-name
  behavior, and existing structural blockers.
- [ ] 2.3 Run the red regressions to green and review the implementation diff for
  broad normalization, native adapter changes, diagnostic changes, or unrelated
  policy behavior.

## 3. Verification And Closeout

- [ ] 3.1 Run focused bridge and adjacent hydration pytest with a fresh writable
  basetemp, `py_compile`, `git diff --check`, and strict change plus global
  OpenSpec validation.
- [ ] 3.2 Run the partitioned repository `commit` test gate instead of a raw
  unregistered full pytest suite, and confirm no native environment, seed,
  gameplay, model, reward, OPE, formal-RL, training, qualification, loading, or
  promotion surface was touched.
- [ ] 3.3 Update project direction, sync the delta requirement, archive the
  completed change, commit the cohesive repair, and push `master` while
  preserving unrelated local artifacts.
