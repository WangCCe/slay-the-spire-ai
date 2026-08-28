## 1. Regression Contract

- [x] 1.1 Add failing tests for exact registration/source/input validation, fixed recipe validation, and refusal to overwrite completed output.
- [x] 1.2 Add failing tests for deterministic two-stage fitting, development-only threshold calibration, legal changed-row action fitting, and frozen parent identity.
- [x] 1.3 Add failing tests for per-replay fixed eligibility gates, strict adapter round trip, atomic reporting, and development-only authority.

## 2. Candidate Fit Runner

- [x] 2.1 Implement validated loading of the registered LightSTS, parent, development replay, and evaluation replay inputs without modifying them.
- [x] 2.2 Implement the fixed simulator-pretrained gate, development gate refinement, changed-only action fit, and threshold calibration recipe.
- [x] 2.3 Implement independent replay scoring, all-replay eligibility, strict artifact restoration, atomic report publication, and practical infrastructure retry behavior.

## 3. Verification And Execution

- [x] 3.1 Run focused runner and adjacent adapter/POC/replay tests, strict OpenSpec validation, and the optimized commit gate once at the implementation boundary.
- [x] 3.2 Commit and push the runner, then create and commit a registration bound to that exact source commit and the already confirmed input identities.
- [ ] 3.3 Run one bounded CPU development fit, publish the report and non-production artifact, and verify no game, CommunicationMod, online training, or production checkpoint mutation occurred.
- [ ] 3.4 Decide the fresh gameplay evaluation go/no-go from the fixed report without tuning the completed cohort in place.
