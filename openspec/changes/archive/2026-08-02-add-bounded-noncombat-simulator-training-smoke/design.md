## Context

The archived simulator-adapter POC binds a local `sts_lightspeed` source tree
and exposes deterministic route, shop, event, and card-reward decisions through
an optional native module. Its 20-seed fit audit passed interface checks but the
declared first-candidate policy lost every run. Existing non-combat learning is
a supervised Current/Bottled candidate-ranker pilot over live-derived samples;
it does not exercise an environment or define an RL reward.

This change is the narrow bridge between those two facts. It tests an offline
policy-gradient loop while preserving the current prohibition on formal RL,
live loading, gameplay evaluation, and promotion. Production gameplay remains
on Windows CommunicationMod and must not import any smoke module.

The first native learning integration exposed two POC gaps that the 20-seed fit
did not reach: `GameContext` copies share `shared_ptr<Map>`, so a clone that
enters a new Act mutates the source map, and `ScreenStateInfo` contains
uninitialized encounter/HP fields that the adapter exported unconditionally.
It also confirmed that the dynamic MinGW adapter must load before PyTorch's
Windows DLL set. These are environment-contract defects, not policy results,
and must be repaired before registering the smoke.

## Goals / Non-Goals

**Goals:**

- Prove or falsify that the simulator adapter can drive a deterministic,
  candidate-legal, bounded policy-gradient smoke.
- Pre-register source identity, train/holdout seeds, features, reward,
  optimizer, limits, evaluation, and verdict rules before executing the smoke.
- Measure the paired holdout effect of training without selecting a favorable
  seed set, hyperparameter, or rerun.
- Publish reproducible offline artifacts that remain a separate evidence class.

**Non-Goals:**

- Formal or long-running RL training, reward search, hyperparameter tuning, or
  model architecture selection.
- Simulator/live mechanics equivalence, causal OPE, supported-victory claims,
  live qualification, gameplay launch, policy loading, or promotion.
- Bottled imitation or use of Current/Bottled labels as reward.
- Changes to the external simulator checkout, CommunicationMod configuration,
  live launchers, or production checkpoints.

## Decisions

### 1. One immutable registration controls the smoke

The checked-in input binds the archived fit input/report hashes, simulator
physical-source identity, submodule commits, adapter source commit/hash, native
module hash, Python/compiler identity, algorithm and feature versions, reward
constants, optimizer values, exact seeds, bootstrap settings, and hard resource
limits. Identity drift or an unregistered value fails before rollout.

The only registered execution uses model seed `0`, train seeds `1000..1031`,
holdout seeds `2000..2063`, four train passes, at most 500 target decisions per
episode, at most 128 train episodes per execution, and a 600-second wall limit
per execution. It runs once for publication and once with the identical input
for reproduction. No parameter-changing retry is allowed.

The initial draft used 64 train seeds over eight passes. Before any registered
policy result was observed, native integration measured about 34 seconds for
two 12-episode executions even after an exact state-once feature optimization.
The draft would therefore approach or exceed 900 seconds per execution. The
smaller registration preserves four-category train coverage and a 64-seed
paired holdout while keeping the smoke operationally bounded.

This is preferable to an exploratory notebook because the main risk is tuning
to a tiny deterministic simulator cohort after observing the result.

### 2. Repair clone, snapshot, and native/PyTorch determinism first

The adapter copy constructor deep-copies the current map after copying
`GameContext`, so route and Act transitions on a clone cannot rewrite the
source branch. New environments initialize `info.encounter` to `INVALID`, and
the event snapshot omits upstream `hpAmount0..2` until event-specific validity
can be proven; those fields are otherwise uninitialized or stale for many
screens. Repeated policy-input hashes, not only terminal rows, verify the full
decision sequence.

On Windows, the CLI imports and loads the native module plus its selected MinGW
DLL directory before lazily importing PyTorch. Loading PyTorch first binds an
incompatible runtime DLL and makes the `.pyd` fail to load. Native coexistence
is therefore exercised in a fresh subprocess by the integration gate.

These repairs change adapter source and module identities, so the original fit
report is stale for training. The adapter fit audit must be rerun and pass under
the repaired physical identity before the smoke input can be frozen.

### 3. Reuse the candidate ranker with a simulator-only feature view

The smoke reuses the linear, action-masked `CandidateRanker` with hash dimension
1024, but initializes it from seed `0`; it does not load the supervised Current
or Bottled artifacts. `noncombat-simulator-policy-features-v1` removes `seed`,
`outcome`, provenance, baseline history, and terminal labels before hashing the
state/candidate pair. Candidate identity and legal decision context remain.

This keeps the first RL experiment small and directly tests the existing
variable-candidate representation. PPO or DQN would add replay/value machinery
and new dependencies before the environment-policy boundary is proven.

### 4. Use a fixed REINFORCE smoke, not a general trainer

For each pass, the policy samples only from the adapter-reported candidate
logits, collects one episode for every registered train seed, computes
return-to-go with discount `1.0`, standardizes returns across that pass, and
performs one full-batch Adam update at learning rate `1e-3`. There is no entropy
coefficient, replay buffer, target network, early stopping, checkpoint resume,
or configurable algorithm selection.

The implementation is deliberately a closed smoke command rather than a
reusable formal-training entry point. Candidate duplication, an unreported
selection, unsupported target semantics, non-finite loss, or a bound violation
blocks publication.

### 5. Reward only simulator progress and victory

For transition `t`, with floors capped to 57:

`r_t = max(0, floor_(t+1) - floor_t) / 57 + I(terminal victory)`

The episodic training target is the undiscounted return-to-go. This reward
telescopes floor progress, gives delayed credit to shop/event/card choices, and
avoids embedding Bottled labels, live outcomes, HP/gold/deck heuristics, or the
current policy. It is explicitly training-only and cannot be interpreted as the
live objective or OPE reward contract.

Alternatives using HP, gold, deck scores, or Bottled agreement were rejected
because they would encode the heuristics this experiment is meant to leave room
for RL to challenge. Victory-only reward was rejected for this smoke because
the fit baseline observed no wins and would likely provide no gradient.

### 6. Evaluate initial versus trained policies on a frozen paired holdout

Before and after training, greedy policies run on the same 64 untouched holdout
seeds. The report includes per-seed terminal floor, outcome, decision count,
category coverage, candidate legality, and paired differences. A deterministic
10,000-resample percentile bootstrap with seed `0` estimates the 95% confidence
interval for mean paired terminal-floor improvement.

Structural success requires complete provenance, disjoint seeds, two identical
training/evaluation results, 100% candidate legality, all four categories,
terminal outcomes, and compliance with every bound. With structural success,
the quality verdict is `holdout_signal` only when the confidence-interval lower
bound is greater than zero; otherwise it is `quality_not_demonstrated`. Either
quality result leaves all downstream authority false. Structural failure is
`blocked`.

This paired gate is more informative than comparing unrelated cohorts, while
the confidence interval prevents a small positive mean from being reported as
evidence on its own.

### 7. Publish canonical artifacts outside live checkpoint discovery

The primary execution writes a canonical trajectory summary, metrics JSON,
Markdown report, canonical tensor serialization, and a hash-closed manifest to
an explicit offline output directory. A same-input replay writes to a temporary
directory and must reproduce model tensors, action selections, metrics, and
canonical report bytes. Measured wall time is kept in a noncanonical execution
journal; the canonical report records only the registered limit and pass/fail
status so timing noise cannot break reproduction.

Publication uses the existing pair/transaction rollback pattern. No artifact
uses a production checkpoint filename or enters live model discovery.

## Risks / Trade-offs

- **Simulator bias may reward behavior that fails live** -> No live authority is
  granted; a later proposal must first add divergence controls and real-game
  evaluation boundaries.
- **A linear policy may underfit the decision problem** -> Treat a no-signal
  result as evidence about this bounded smoke, not as proof that RL is futile;
  do not tune within this change.
- **Fixed training seeds may be memorized** -> Remove seed features and judge
  signal only on disjoint paired holdout seeds.
- **Floor progress gives coarse credit** -> Keep it transparent and
  training-only; do not add heuristic terms after seeing results.
- **Dirty external source identity can drift** -> Bind the physical source hash
  and fail closed before rollout.
- **Shallow simulator copies or undefined fields can fake learning differences**
  -> Deep-copy map ownership, omit fields without screen-valid semantics, and
  compare every policy-input hash across the same-input replay.
- **PyTorch and the dynamic MinGW module can bind incompatible Windows DLLs** ->
  Load the native module before lazy PyTorch import and verify coexistence in a
  fresh process.
- **A crash could leave partial artifacts** -> Publish atomically and retain the
  previous complete artifact set on failure.

## Migration Plan

1. Add red regressions for registration, clone ownership, canonical snapshots,
   native/PyTorch coexistence, feature leakage, reward math, legal masking,
   bounds, seed isolation, deterministic replay, verdicts, and publication.
2. Repair the optional adapter and rerun its fit audit, then implement the
   offline rollout, policy-gradient, evaluation, and report modules without
   touching live imports or launch configuration.
3. Rebuild the optional adapter against the refreshed registered source, run
   focused tests and the repository commit gate, then execute the registered
   smoke once plus its same-input reproduction.
4. Publish the result, update project direction with the actual verdict, sync
   specs, archive the change, and commit only scoped files.

Rollback removes the smoke modules and offline artifacts. There is no runtime
migration and no live configuration or checkpoint to restore.

## Open Questions

None before implementation. Changing a seed, reward term, feature field,
optimizer value, bound, bootstrap rule, or verdict threshold requires an
OpenSpec amendment before another execution.
