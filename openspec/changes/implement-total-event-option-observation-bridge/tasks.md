## 1. Regression Boundary

- [ ] 1.1 Add adapter regressions for native API v3 source identity, exact N'loth offered-relic records, newly loaded module rejection, historical v2 read compatibility, and missing or inconsistent v3 context rejection.
- [ ] 1.2 Add total-resolver regressions for contract path/hash/schema/count closure, all 25 events, 47 aliases, static rules, all five Cursed Tome phases, N'loth slot/id/name validation, Mindbloom normalization, exact provenance, fail-closed drift, and non-mutation.
- [ ] 1.3 Add bridge regressions for dual-coordinate hydration, Cleric and Cursed Tome sparse-index reverse mapping, versioned inline semantics, contiguous legacy inline compatibility, ambiguous legacy rejection, invalid Current positions, and source non-mutation.

## 2. Offline Implementation

- [ ] 2.1 Advance the C++ non-combat adapter to API v3 and export exactly two N'loth offered-relic records from `GameContext.info.relicIdx0/relicIdx1` without changing other event or gameplay behavior.
- [ ] 2.2 Update Python adapter validation to require v3 for newly loaded modules while preserving explicit historical snapshot/provenance readers and never synthesizing v3 fields.
- [ ] 2.3 Replace the Liars Game-only resolver with strict canonical-contract loading and total static, Cursed Tome, N'loth, identity-normalization, and dual-coordinate observation resolution.
- [ ] 2.4 Normalize bridge enrichment and hydration to separate Current positions from simulator indices and map Current actions back through the validated observation without changing `OptimizedAgent`.

## 3. Verification And Closeout

- [ ] 3.1 Run focused adapter, resolver, observation-contract, and bridge pytest with isolated writable basetemp; do not load or execute a native module.
- [ ] 3.2 Run Python compile checks, strict change validation, global OpenSpec validation, and the repository commit test gate; do not substitute the raw long-suite entrypoint or launch gameplay because this path is offline-only.
- [ ] 3.3 Write the implementation closeout and update project direction while keeping compatibility, seed use, gameplay, baseline, reward, model, formal-RL, training, and promotion authority false.
- [ ] 3.4 Sync modified capability specs, archive the completed change, commit cohesive implementation evidence, and push `master` without running a compatibility cohort.
