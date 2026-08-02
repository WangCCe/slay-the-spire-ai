## Context

The archived bounded simulator-training smoke produced a deterministic paired
terminal-floor improvement over its seeded random initialization on holdout
seeds `2000..2063`. Both policies nevertheless won 0/64 runs. That result proves
that the adapter, candidate ranker, reward, and update loop can interact; it does
not prove that the frozen policy beats a competent same-schema decision policy.

The local `sts_lightspeed` checkout already contains `search::SimpleAgent`, which
controls the adapter's non-target screens and exposes its route, shop, event,
and card-reward methods. It is the narrowest meaningful simulator baseline.
The Current-imitation and Bottled-auxiliary pilot models are not valid direct
baselines: they were fitted over live-sample state keys and action identities,
while the simulator uses a different state projection and slot/reward-specific
action ids. Treating them as interchangeable would test an unvalidated bridge
rather than policy quality.

This change performs a separately registered, offline-only policy-validity
study. It extends the optional adapter with a read-only SimpleAgent target-action
query, evaluates three frozen policies on new simulator seeds, and keeps every
formal-training and live authority false. Production gameplay remains on the
Windows CommunicationMod path and does not import this evaluator.

## Goals / Non-Goals

**Goals:**

- Expose the upstream SimpleAgent's target decision as exactly one current
  adapter candidate without changing the queried environment.
- Prove that the adapter extension preserves the already published frozen
  policy's state, candidate, and action semantics before touching fresh seeds.
- Compare the frozen trained ranker with both SimpleAgent and its exact seeded
  initialization on one pre-registered, disjoint 64-seed cohort.
- Separate structural reproducibility, baseline-relevant floor signal, and
  simulator victory observations in canonical artifacts.
- Produce a durable go/no-go input for the next offline phase without starting
  formal non-combat RL or live gameplay.

**Non-Goals:**

- Training, fine-tuning, gradient updates, checkpoint selection, reward search,
  hyperparameter tuning, seed selection, or policy promotion.
- Direct execution of the Current-imitation or Bottled-auxiliary pilot models
  before a separately validated simulator feature/action bridge exists.
- Simulator/live mechanics equivalence, causal OPE, qualification, live policy
  loading, gameplay launch, or collection of new `.run` and trace evidence.
- Changes to the external simulator checkout, CommunicationMod configuration,
  launchers, production checkpoints, or gameplay policy code.

## Decisions

### 1. Use three frozen policies with one primary comparison

The candidate policy is the canonical final model from
`reports/noncombat_simulator_training_smoke_20260802/model.json`. The replication
control is the exact `CandidateRanker(input_dim=1024)` initialization produced by
model seed `0`. The meaningful baseline is `sts_lightspeed` SimpleAgent choosing
only the four target categories while the adapter continues to control combat
and unsupported screens exactly as it did in the smoke.

All policies are greedy and run in independent environments. The registered
primary estimand is trained terminal floor minus SimpleAgent terminal floor,
paired by seed. Trained minus seeded initialization is a secondary replication
estimand and cannot satisfy the primary gate. Victory counts and paired victory
differences are reported separately; a floor signal with zero trained victories
is not a victory-quality claim.

Current and Bottled pilot artifacts are listed as excluded baselines with their
bound identities and incompatibility reasons, but their weights are not loaded
or executed. A direct transfer was rejected because it would silently hash
unseen simulator fields and fail to preserve live action identity.

### 2. Query upstream SimpleAgent rather than copy its rules

The adapter API is versioned forward and exposes a native-baseline action query.
For the current category, it deep-copies the `GameContext` and SimpleAgent
continuation state, invokes the corresponding public SimpleAgent method, and
maps the resulting `GameAction.bits` to exactly one current candidate. Card
reward index `5` maps explicitly to the adapter's skip or Singing Bowl candidate.
Zero or multiple matches fail closed.

SimpleAgent carries a map path across route decisions. The adapter therefore
tracks whether an environment has followed the queried native target action at
every prior target state and carries the probed path state forward only when the
matching action is applied. The query is supported for this native-baseline
trajectory, which is the only trajectory used by the baseline evaluator. It is
not advertised as a counterfactual oracle after another policy deviates.

The query itself must leave canonical snapshot bytes, candidate bytes, and clone
state unchanged and must return the same action on repetition. This is preferable
to reimplementing SimpleAgent's event, shop, card, and route rules in Python,
which would create an unversioned second policy.

### 3. Refresh adapter fit, then prove frozen-policy compatibility

The adapter API/source/module identities change, so the prior fit report cannot
authorize the study directly. The fit audit is rerun under the new physical
identity and gains focused coverage for deterministic candidate mapping,
non-mutation, all four categories, card skip/Bowl handling, and route
continuation on a baseline-controlled trajectory.

Before any fresh-cohort rollout, a compatibility gate reconstructs the initial
ranker and loads the frozen final model, then replays seeds `2000..2003`. For both
rankers it requires exact equality with the published smoke trajectories for
every policy-input hash and selected action id. These old seeds test environment
and model identity only. Their outcomes do not enter the new quality estimate.

Any compatibility mismatch blocks the study. It is not repaired by changing
features or accepting a close result because that would redefine the frozen
candidate after its holdout was observed.

### 4. Freeze one new cohort and finite evaluation budget

The checked-in registration binds the smoke registration, model, trajectories,
manifest and their hashes; the refreshed fit evidence; physical simulator,
submodule, adapter, module, Python, compiler, PyTorch, feature, and evaluator
identities; excluded-baseline evidence; exact policy order; bootstrap settings;
and all limits.

The study uses ascension `0`, compatibility seeds `2000..2003`, and fresh seeds
`3000..3063`. The fresh cohort is disjoint from fit seeds `0..19`, train seeds
`1000..1031`, smoke holdout seeds `2000..2063`, and compatibility execution.
Each policy may run at most 64 fresh episodes and 500 target decisions per
episode. One execution may run at most 192 fresh episodes and 480 seconds. It is
executed once for publication and once with identical input for reproduction.

There is no training mode, optimizer, autograd-enabled rollout, alternate seed
set, early selection, or parameter-changing retry. A bound failure publishes a
blocker and stops.

### 5. Use a paired bootstrap gate without promotion semantics

For each pairwise comparison the evaluator computes mean terminal-floor
difference and a deterministic 95% percentile-bootstrap interval with 10,000
resamples and bootstrap seed `0`. The primary baseline signal is demonstrated
only when the trained-minus-SimpleAgent interval lower bound is greater than
zero. The initial-control interval is descriptive replication evidence only.

Structural validity requires exact provenance, successful compatibility,
unique disjoint seeds, three complete terminal rows per seed, candidate legality,
aggregate four-category coverage, finite metrics, registered bounds, immutable
model hashes, and exact same-input reproduction. Structural and quality verdicts
are independent: a valid study may report that baseline signal was not
demonstrated, and then stops without adaptation.

### 6. Publish canonical evidence outside model discovery

The primary execution and identical replay produce canonical policy trajectories,
paired metrics, a Markdown report, and a hash-closed manifest. Wall-clock timing
and failure diagnostics are kept in a noncanonical execution journal. Atomic
publication retains the prior complete artifact set if validation or replacement
fails.

Every artifact records the registration hash and marks formal non-combat RL,
simulator training, live gameplay, live loading, live study launch, OPE,
qualification, and promotion authority false. A positive primary floor gate can
support only a new reviewed offline proposal; it cannot directly unlock training.

## Risks / Trade-offs

- **SimpleAgent is a weak or idiosyncratic baseline** -> Label its exact version
  and target-only role; report absolute floors and victories alongside deltas.
- **SimpleAgent route choice is historyful** -> Restrict the query to a
  baseline-following target trajectory and test route continuation explicitly.
- **Adapter changes alter the frozen policy input** -> Require exact published
  input/action replay on four old holdout seeds before fresh evaluation.
- **A 64-seed interval can miss small effects** -> Report the interval and stop;
  do not enlarge or replace the cohort after observing it.
- **Terminal floor rewards survival without winning** -> Keep victory evidence
  separate and retain zero-victory limitations even if the floor gate passes.
- **Simulator divergence can produce misleading quality** -> Preserve the
  simulator-only evidence class and every downstream authority flag as false.
- **A long replay can waste iteration time** -> Enforce a 480-second bound per
  execution and use the repository commit gate instead of an unbounded raw suite.

## Migration Plan

1. Add red regressions for native action mapping, non-mutation, route continuity,
   card skip/Bowl mapping, wrapper validation, and fail-closed behavior.
2. Extend and rebuild the optional adapter, rerun its fit audit, and record the
   refreshed physical identity without modifying the external checkout.
3. Add red regressions and implement frozen model loading, compatibility replay,
   registration validation, three-policy rollout, paired metrics, reproduction,
   atomic artifacts, and all-false authority.
4. Commit the reviewed implementation and one immutable registration before any
   fresh seed is evaluated.
5. Run focused/native checks and the registered commit gate, then execute one
   primary study and one identical reproduction. Publish any passing, negative,
   or blocked result without tuning.
6. Update project direction, sync specs, archive the change, and commit only the
   scoped files while preserving unrelated local artifacts.

Rollback removes the optional query, evaluator, tests, registration, and study
artifacts. There is no live runtime migration or production checkpoint to
restore.

## Open Questions

None before implementation. Changing a model, policy order, seed, metric,
bootstrap rule, confidence threshold, compatibility subset, or resource bound
requires an OpenSpec amendment before another fresh execution.
