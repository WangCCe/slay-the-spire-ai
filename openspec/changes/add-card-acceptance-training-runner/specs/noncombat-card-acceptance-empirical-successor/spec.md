## ADDED Requirements

### Requirement: Training authority waits for a reviewed executable runner
The empirical successor SHALL keep the pushed r6 registration and bounded
training request immutable and request-only until one exact training runner,
launch-manifest schema, closed command set, source-only preflight, independent
verifier, focused tests, registered repository gates, and text-only source
review are committed and pushed. Parent task 6.4 SHALL remain incomplete until
one exact r6 launch manifest is independently reviewed and pushed, and task 6.5
SHALL remain blocked until separate valid approval and launch observations exist.

#### Scenario: Request exists but runner is absent
- **WHEN** the r6 training request is reviewed and pushed but no reviewed executable runner/manifest boundary exists
- **THEN** request publication remains valid while authorization, native/model loading, environment construction, seed access, and training remain ineligible

#### Scenario: Runner source boundary is complete
- **WHEN** runner source, tests, launch-manifest schema, source-only preflight, independent verification, configured gates, and review are pushed without empirical access
- **THEN** only publishing the deterministic zero-progress control anchor and then rendering/reviewing one exact launch manifest become eligible; authorization and execution remain separate later boundaries
