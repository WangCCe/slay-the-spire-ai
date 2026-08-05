## Why

The final Current baseline lane is closed with no viable policy-quality
candidate, but that does not prevent a bounded simulator experiment from
testing whether the already implemented state-conditioned ranker can learn
without the deterministic state-cancellation and card-take collapse observed
in r2. Separating a frozen training control from a credible policy baseline
allows useful RL architecture evidence now while formal RL, live value, and
promotion remain blocked.

## What Changes

- Add a new simulator-only experiment runner that combines exact API v3
  separate state/candidate tensors with the versioned state-conditioned MLP
  ranker; do not modify the r2-bound runner or artifacts.
- Define a frozen seeded initialization as the paired experimental control,
  never as policy-quality truth, reward, teacher, or promotion evidence.
- Add deterministic anti-collapse diagnostics and canary gates for candidate
  opportunities, selected action kinds, score margins, state sensitivity, and
  category coverage alongside paired floor and victory outcomes.
- Preserve the formal victory-primary reward, conservative unsupported-episode
  accounting, deterministic replay, fresh train/canary/holdout isolation,
  bounded CPU execution, atomic evidence, and independent no-native verifier.
- Separate source-only implementation, pushed preregistration, exact execution
  authorization, one logical execution, and terminal closeout. The current
  baseline and known-propensity outcome lanes remain immutable and blocked.
- Treat the absence of source-comparable target-supported victories as the
  current live-evidence state. The experiment cannot create or substitute that
  evidence.

Success requires legal replay-identical rows, four-category coverage, bounded
support failures, a positive preregistered paired floor signal, explicit
victory accounting, and no registered action-family collapse. A zero-victory
or floor-only positive result remains simulator architecture evidence and does
not establish policy quality or formal-RL readiness.

Non-goals include choosing a new heuristic quality baseline, imitating
SimpleAgent or Bottled, changing formal readiness or reward semantics,
resuming Current or r2, launching Slay the Spire or CommunicationMod, loading
production checkpoints, OPE, live qualification, and promotion.

The rollback boundary is additive: before a started journal, validation may be
repeated with no empirical effect; after start, any structural, resource,
publication, or gate failure consumes the logical experiment, preserves the
last complete evidence, and permits no retry, seed replacement, tuning, or
in-place repair.

## Capabilities

### New Capabilities

- `noncombat-state-conditioned-simulator-learning-experiment`: Defines the
  isolated state-conditioned runner, frozen initialization control,
  anti-collapse and learning gates, bounded lifecycle, canonical publication,
  and no-live-authority boundary.

### Modified Capabilities

None. Historical simulator, formal-readiness, baseline, reward, and outcome
requirements remain unchanged.

## Impact

- New analysis runner and standalone verifier under `analysis_scripts/`.
- New focused tests under `tests/` and canonical planning/evidence reports
  under `reports/`.
- Reuses `noncombat_state_conditioned_policy_input`,
  `noncombat_state_conditioned_ranker`, the API v3 simulator adapter, and the
  formal reward contract without changing their historical evidence.
- Uses Windows CPU execution with the bound native `sts_lightspeed` module only
  after a separate pushed registration and exact authorization.
- No production agent, CommunicationMod configuration, gameplay policy,
  checkpoint, OPE, formal-RL, qualification, loading, or promotion surface is
  changed.
