## Why

The simulator-training smoke already demonstrated legal candidate-masked RL,
deterministic replay, and a positive paired floor signal, while the formal
state/action, reference-isolation, reward, and evaluation domains now pass.
Continuing to block every offline learning step on the consumed Current
baseline study and unavailable live target-supported outcomes conflates a
simulator experiment with a policy-quality or promotion claim.

## What Changes

- Add a separately registered, simulator-only non-combat RL experiment that
  uses the current API v3 adapter and the validated formal victory-primary
  reward contract. It does not alter or rerun the frozen training smoke.
- Add a finite candidate-masked training runner with deterministic
  checkpoint/resume, fixed train/canary/holdout isolation, legal-action checks,
  explicit CPU/GPU and wall-time bounds, and atomic artifacts outside live
  checkpoint discovery.
- Fix one algorithm, feature contract, optimizer, cohort generator, training
  budget, canary gate, holdout gate, bootstrap method, stop rule, and replay
  prefix before execution. No hyperparameter sweep or post-result retry is
  permitted inside this change.
- Make terminal simulator victory the primary optimization and evaluation
  objective. Floor progress remains bounded secondary shaping and diagnostics;
  Current, Bottled, SimpleAgent, live outcomes, and OPE values remain excluded
  from reward.
- Compare the frozen trained policy with its frozen initialization on one
  disjoint holdout. Record victory counts/rates first and paired terminal-floor
  evidence second; report every unsupported episode conservatively without
  dropping or replacing it.
- Require implementation, registration, and source-only verification to be
  committed and pushed before a separate one-shot execution authorization is
  created. Native loading, environment construction, seed use, and training
  remain false until that execution gate is satisfied.
- Preserve the formal-readiness verdict
  `not_ready_for_bounded_training_proposal`. Even a successful experiment does
  not demonstrate a Current baseline floor, live source comparability,
  target-supported outcomes, causal uplift, or promotion readiness.

Live evidence remains deliberately insufficient: the repository has one
historical Ironclad A0 victory, but the formal outcome-support audit has zero
source-comparable target-supported victories and plug-in pass probability
zero. The existing simulator smoke trained on 128 episodes and improved paired
holdout floor by `2.921875` with 95% interval `[1.703125, 4.171875]`, but both
initial and trained policies won `0/64`. This experiment succeeds structurally
only if legality, isolation, bounds, checkpoint replay, and publication pass;
its preregistered learning gate must require trained holdout victories to
exceed initialization and a positive paired floor signal. Failure is a valid
terminal experiment result, not permission to tune or rerun.

No live game, Communication Mod configuration, production checkpoint, Current
policy, gameplay heuristic, Bottled adapter, OPE estimate, formal-readiness
artifact, or historical study artifact may be changed. Rollback removes only
the new runner, registration, tests, artifacts, and synced capability clauses;
all prior smoke, readiness, baseline, outcome, and gameplay evidence remains
immutable.

## Capabilities

### New Capabilities

- `noncombat-simulator-rl-experiment`: Define a provenance-bound, bounded,
  resumable simulator-only RL experiment with victory-primary reward, isolated
  evaluation, fail-closed publication, and no live or promotion authority.

### Modified Capabilities

- `noncombat-simulator-adapter`: Permit the API v3 adapter to serve an accepted
  bounded simulator RL experiment only within its exact registration and
  resource limits, while retaining all live and formal-RL prohibitions.

## Impact

- Expected implementation: a new experiment runner plus narrowly reused
  feature/model/adapter helpers under `analysis_scripts/`; no production agent
  entrypoint changes.
- Expected tests: source-only registration, reward, masking, checkpoint,
  isolation, publication, verifier, and negative-authority regressions; native
  integration tests remain separately marked and bounded.
- Expected artifacts: a checked-in preregistration and an isolated external or
  report-root experiment directory with canonical configuration, journal,
  checkpoints, trajectories, metrics, report, and manifest.
- Runtime: Windows Python and the explicitly bound `sts_lightspeed` native
  module only after the separate execution gate; no Communication Mod process.
- Dependencies: reuse PyTorch and existing repository code; add no package or
  live runtime dependency unless design evidence proves it necessary.
