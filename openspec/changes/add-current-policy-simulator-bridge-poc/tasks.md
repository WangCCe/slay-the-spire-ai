## 1. Registration And Frozen Evidence

- [x] 1.1 Define the source-bound POC registration schema, Current configuration, frozen-row selection, category quotas, replay count, and all-false authority contract.
- [x] 1.2 Validate and hash-bind Current/bridge sources, simulator adapter identity, frozen demonstrations, external metadata, runtime, and expected outputs before evaluation.

## 2. Bridge Core

- [x] 2.1 Add regressions for exact route, shop, card-reward, and event action mapping, including duplicate names, bowl/skip, purge/leave, missing event semantics, and absent/ambiguous matches.
- [x] 2.2 Implement validated snapshot hydration with source-slot identity, typed screen state, canonical non-mutation checks, and field-specific fail-closed errors.
- [x] 2.3 Implement exact `OptimizedAgent` invocation with fixed Ironclad configuration, tracking/gameplay I/O disabled, optimized-component and fallback guards, and episode-local state isolation.
- [x] 2.4 Implement category-specific one-to-one candidate mapping without name-first fallback.

## 3. Frozen Structural POC

- [x] 3.1 Select only preregistered rows from the existing frozen dataset and verify source identity, row order, and registered category coverage.
- [x] 3.2 Run deterministic replay and non-mutation checks and publish per-row hydration, mapping, fallback, and failure-reason evidence.
- [x] 3.3 Emit the Stage 1 structural verdict and authorize Stage 2 only when every registered gate passes.

## 4. Conditional Stateful Compatibility

- [x] 4.1 Validate the Stage 1 authorization and reused-seed registration, then either execute the one bounded stateful compatibility run or record the fail-closed reason it was not run.
- [x] 4.2 Publish Stage 2 legality, determinism, session-isolation, and trajectory evidence if execution is authorized; otherwise preserve the explicit no-execution/no-trajectory status.

## 5. Verification And Closeout

- [x] 5.1 Run focused bridge tests, adjacent non-combat simulator regressions, the commit test gate, and strict OpenSpec validation; do not launch fresh gameplay for this analysis-only change.
- [x] 5.2 Recompute the canonical report from its registration, verify artifact hashes and all-false authority, update the project-direction/readiness evidence with the bounded result, and commit the cohesive change.
