## Why

The terminal r2 postmortem found that the registered linear ranker scores
`shared_state + candidate`, so shared state-only features cancel exactly from
relative logits. The same evidence showed zero victories in 5,376 policy
episodes and a final greedy policy that took every observed canary and holdout
card reward; another simulator run would spend a fresh cohort without first
fixing the demonstrated capacity blocker.

## What Changes

- Add a versioned, CPU-only non-combat candidate ranker whose relative scores
  can depend on both decision state and candidate identity.
- Add an explicit state-sensitivity regression: changing only state for an
  unchanged legal candidate set must be able to reverse candidate ordering.
- Add deterministic repeat, legal-mask, finite-value, serialization, and
  candidate-order regressions for the new ranker boundary.
- Add reusable anti-collapse diagnostics for candidate availability, selected
  action-family rates, skip/take behavior, and score margins by category.
- Preserve the r2 runner, verifier, model, reports, source-bound files, and
  terminal verdict byte-for-byte.
- Keep experiment execution, new cohort access, training, replay, gameplay,
  CommunicationMod, model loading, formal RL, qualification, and promotion out
  of scope.

Success means focused regressions prove state-sensitive ordering and stable
diagnostics, all existing r2 verification remains valid, and the repository
test gates pass without native loading or gameplay. There is no live-gameplay
claim: the triggering evidence is the closed simulator-only r2 artifact and
source algebra, not a new `.run`.

Rollback is removal of the new versioned ranker/diagnostic implementation,
tests, and capability spec. No historical artifact, production runtime path,
checkpoint, or existing v1 ranker requires migration.

## Capabilities

### New Capabilities

- `noncombat-state-conditioned-ranker`: Defines versioned state/action scoring,
  state-sensitivity and determinism invariants, anti-collapse diagnostics, and
  all-false execution/live authority.

### Modified Capabilities

None. The historical `noncombat-simulator-rl-experiment` contract remains
unchanged and continues to describe the completed r1/r2 executions.

## Impact

- New development-only modules under `analysis_scripts/`: a Torch ranker
  boundary and a separately importable standard-library diagnostic summarizer.
- New focused tests under `tests/`; existing r2 source-bound implementation
  files are not edited.
- No new package dependency, native module load, CommunicationMod change,
  production checkpoint change, model migration, seed registration, or
  experiment authorization.
