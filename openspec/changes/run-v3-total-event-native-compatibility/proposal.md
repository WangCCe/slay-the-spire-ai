## Why

The total event observation bridge now has complete unit and repository-gate
coverage, but no adapter API v3 module has been built or exercised on a native
own-trajectory run. The historical r2 compatibility attempt used API v2,
consumed seeds `2000..2003`, and stopped at `The Cleric`; it cannot authorize a
retry or establish compatibility for the new total resolver and dual-coordinate
mapping.

This change creates one independently preregistered structural compatibility
evaluation. It consumes no live `.run`, Communication Mod log, or gameplay
evidence. Success means every fixed native trajectory is legal, terminal,
deterministic, and processed through the exact Current policy and total event
contract; it does not mean that Current is a competent baseline.

## What Changes

- Add a new versioned native-compatibility registration and evaluator instead
  of changing or inheriting the historical reused-seed Stage 2 authorization.
- Require a staged boundary: commit and verify the evaluator, build and inspect
  an API v3 module without constructing an environment, publish and push the
  hash-closed registration, and only then permit seed access.
- Bind the module hash and build identity, adapter and simulator physical source
  identities, submodules, total observation contract, Current bridge and policy
  implementation, metadata, runtime, prior seed ledger, output contract, and
  all-false authority.
- Freeze exactly seeds `7000..7007`, two replays per seed, at most 500 target
  decisions per replay, and a 120-second execution bound. The cohort is
  disjoint from prior fit, smoke, policy-validity, warm-start, reserved final,
  and consumed bridge cohorts.
- Mark the entire cohort consumed when the first native environment is
  constructed. A blocker, timeout, crash, or partial result is final for this
  registration; no seed replacement, threshold change, or same-identity retry
  is allowed.
- Pass only if all eight seeds terminate, replay trajectories match exactly,
  every selected action is a reported legal candidate, no Current fallback,
  tracker activity, or source mutation occurs, and aggregate route, shop,
  event, and card-reward coverage is nonzero.
- Record encountered event identities and coordinate mappings diagnostically;
  absence of a particular rare event such as N'loth does not claim or disprove
  its full native coverage beyond the registered contract regressions.
- Publish canonical configuration, trajectory rows, metrics, report, execution
  journal, and manifest, then independently verify them without constructing
  another environment.
- Keep gameplay, baseline-floor measurement, outcome support, reward changes,
  model fitting, formal RL training, qualification, and promotion out of scope.

## Capabilities

### New Capabilities

- `noncombat-total-event-native-compatibility`: Define staged preregistration,
  physical identity closure, fixed fresh-cohort execution, deterministic native
  trajectory gates, one-shot consumption, canonical publication, and
  structural-only authority for the API v3 total event bridge.

### Modified Capabilities

- `noncombat-current-policy-simulator-bridge`: Add a new preregistered native
  compatibility path that preserves historical v1/v2 registrations, does not
  inherit consumed Stage 2 authorization, and evaluates Current event actions
  through the total observation mapping on a new fixed cohort.

## Impact

- Expected implementation surfaces are a new offline compatibility module and
  focused tests, plus narrow reusable bridge helpers if required. It does not
  change `OptimizedAgent`, Communication Mod, live gameplay, reward, or model
  code.
- The adapter is built out of tree against the explicit local
  `D:\CLionProjects\sts_lightspeed` checkout with production Python ABI. The
  external checkout remains read-only and the generated module remains ignored
  build output identified only by content hash and build metadata.
- Registration and result artifacts are new immutable evidence. Existing API
  v2 modules, bridge registrations, consumed seeds, reports, and the canonical
  observation contract remain byte-for-byte unchanged.
- Rollback removes only the new evaluator and unexecuted registration tooling.
  Once seed access begins, its registration, journal, and pass or fail result
  are retained permanently even if implementation code is later reverted.
