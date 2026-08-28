## 1. Exact Proposal Provenance

- [x] 1.1 Add RED agent regressions for unchanged proposals, changed same-state proposals, no-proposal takeover, illegal emitted actions, and immutable proposed-action identity.
- [x] 1.2 Add RED replay regressions for schema-v3 round trip, known-row consistency, schema-v1/v2 legacy-unknown restoration, and unchanged default sampling.
- [x] 1.3 Implement pending-transition attribution and compatible replay persistence with exact proposal indices and sentinels.

## 2. Candidate-Decision SMDP Builder

- [x] 2.1 Add RED coverage for direct adjacency, multi-row takeover spans, terminal spans, uncontrolled prefixes, terminal-combat partition isolation, unknown rejection, and source-row reconciliation.
- [x] 2.2 Implement deterministic candidate-decision span construction with accumulated discounted rewards, variable bootstrap multipliers, source identities, and telemetry.

## 3. Fixed Development Runner

- [x] 3.1 Add RED coverage for immutable callability bindings, exact 64-update recipe, direct/changed-only batches, variable-discount TD, fixed gates, and no-authority reporting.
- [x] 3.2 Implement atomic callability-filtered fitting and reporting without changing production trainer defaults or checkpoint loading.
- [x] 3.3 Run focused tests, strict OpenSpec validation, and one optimized commit gate; commit and push the implementation boundary.

## 4. Fresh Callability Collection

- [ ] 4.1 Bind the implementation commit, production-r16 checkpoint, ten unused seeds, zero-update launch config, collection checks, fixed fit recipe, and output paths in an immutable registration; validate, commit, and push it before gameplay.
- [ ] 4.2 Execute the bounded Windows CommunicationMod collection, preserve runtime evidence, restore the previous config, and stop project Python and game processes after completion or failure.
- [ ] 4.3 Audit `.run`, debug, error, trace, inventory, checkpoint, action legality, proposal legality, class reconciliation, direct eval-parent parity, and SMDP span integrity; commit and push the collection decision.

## 5. Bounded Callability-Filtered Fit

- [ ] 5.1 If every pre-fit gate passes, execute the registered CPU fit once and independently audit updates, batches, spans, hashes, technical gates, and authority without changing the recipe.
- [ ] 5.2 Commit and push the result, sync the delta specs, and archive the completed change. If a fixed gate fails, stop the corpus and record residual/separate-head as the next change.
