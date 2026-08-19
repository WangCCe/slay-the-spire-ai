## 1. Objective Implementation

- [x] 1.1 Add default-off validated end-turn margin guard configuration and frozen-parent reuse to `DQNTrainerV2`
- [x] 1.2 Compute clipped parent margins, candidate hinge loss, eligibility, and ranking-violation metrics
- [x] 1.3 Thread guard configuration and objective summaries through the LightSTS smoke runner and simulator-only checkpoint metadata

## 2. Regression And Verification

- [x] 2.1 Add mathematical regressions for eligible, ineligible, zero-row, and clipping behavior
- [x] 2.2 Add default compatibility, invalid configuration, warm-start, report, and checkpoint binding regressions
- [x] 2.3 Run focused pytest and the repo's bounded commit test gate; record any broader-suite limitation rather than spending the experiment budget on known unrelated failures
- [x] 2.4 Run strict OpenSpec validation

Verification: affected files passed `69 passed, 5 skipped`. The one bounded commit gate completed with `4,741 passed, 26 skipped, 20 failed`; failures were outside changed files and grouped under an old simulator fixture field, historical noncombat source-identity drift, and event-policy AST binding drift. The gate was not rerun.

## 3. Bounded Experiment

- [ ] 3.1 Preregister one fresh-seed production-r16 simulator-shadow successor with fixed guard weight, cap, gates, and rollback boundary
- [ ] 3.2 Execute the registration once without game or CommunicationMod access and publish immutable technical and matched-outcome evidence
- [ ] 3.3 Decide go/no-go from the registered gates, retain production r16 on any miss, and sync/archive the completed change
