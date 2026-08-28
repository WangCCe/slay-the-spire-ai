## 1. Fresh Replay Registration

- [x] 1.1 Generate ten collision-free seeds and bind the zero-update r16 launch configuration, 64-update recipe, and stratified gates before collection.
- [x] 1.2 Strictly validate, commit, and push the complete OpenSpec change and replay registration.

## 2. Fresh Replay Collection

- [x] 2.1 Execute exactly ten registered r16 games, restore CommunicationMod configuration, and stop residual game processes.
- [x] 2.2 Publish the checkpoint, run records, runtime traces, and parity audit; block fitting unless every collection gate passes.
- [x] 2.3 Commit and push the immutable replay evidence and bound checkpoint hash.

## 3. Stratified Successor Runner

- [x] 3.1 Add RED coverage for 64-update fitting and direct-drift versus override-uplift eligibility.
- [x] 3.2 Reuse the existing full-network fitter with the new immutable replay and provenance-stratified report gates.
- [x] 3.3 Run focused tests, strict OpenSpec validation, and one qualified commit gate at the completed code boundary.

## 4. Bounded Training

- [x] 4.1 Execute the registered 64-update recipe exactly once on the fresh corpus.
- [x] 4.2 Audit candidate hashes and every stratified gate without same-corpus tuning or rerun.
- [x] 4.3 Commit and push the result, then sync and archive the change; register a fresh holdout only on an all-pass decision.
