## Context

The B3-B7 known-propensity pool contains 1,253 confirmed decisions grouped into
125 complete run trajectories. Deterministic Current has 87 nonzero-weight
trajectories, ESS 66.30, ESS fraction 0.5304, and maximum normalized weight
0.04454, so the existing overlap screen passes. The pool has only one victory,
however, and the current readiness implementation deliberately computes no
policy value or confidence interval.

The existing `noncombat_ope_readiness` module already owns strict source,
target-policy, trajectory, exact-weight, and overlap contracts. The independent
artifact verifier can replay those contracts without importing the readiness
implementation. Estimator work must consume that verified boundary rather than
weaken or duplicate it, must operate on complete trajectories, and must remain
outside production gameplay and checkpoint paths.

## Goals / Non-Goals

**Goals:**

- Implement exact trajectory-level target and behavior value accounting for
  victory and floor-reached channels.
- Add deterministic paired whole-trajectory uncertainty and influence
  diagnostics.
- Validate estimator arithmetic and interval behavior against identity,
  synthetic known-truth, exact bootstrap-enumeration, and coverage fixtures.
- Separate estimator implementation readiness, real-dataset estimate
  generation, and candidate-superiority conclusions.
- Produce independently replayable B3-B7 artifacts without enabling training
  or live policy changes.

**Non-Goals:**

- No doubly robust estimator, learned outcome model, cross-fitting, clipping,
  weight capping, per-decision return, or reward shaping.
- No claim that floor reached substitutes for terminal victory.
- No formal non-combat RL training, target-policy optimization, policy mixture,
  CommunicationMod change, live promotion, or gameplay policy edit.
- No causal-effect claim from an observational policy-value difference.

## Decisions

### 1. Preserve the estimate-free readiness boundary

`analysis_scripts.noncombat_ope_estimation` accepts canonical samples, the
target manifest, its readiness artifact, and a calibration artifact. It first
requires the existing independent artifact verifier to pass and requires the
readiness artifact's overlap gate to be true. It then consumes the verified
exact trajectory weights and one terminal outcome per run.

The estimator does not add estimate fields to the existing readiness artifact.
It writes a separately versioned `noncombat-ope-estimate-v1` JSON/Markdown pair
bound to every input SHA-256 and effective configuration. This keeps B2 and all
estimate-free audits reproducible and avoids changing their meaning.

Alternative: extend `noncombat_ope_readiness.py` directly. Rejected because it
would mix source/overlap validation with statistical estimation and make the
independent precondition harder to audit.

### 2. Use SNIS as primary and OIS as a diagnostic

For trajectory weight `w_i`, outcome `y_i`, and `n` complete trajectories:

- ordinary trajectory IS is `sum(w_i * y_i) / n`;
- self-normalized trajectory IS is `sum(w_i * y_i) / sum(w_i)`;
- behavior value is the unweighted `sum(y_i) / n`;
- policy-value difference is target value minus behavior value on the same
  trajectory sample.

All point estimates are computed as exact `Fraction` values before finite float
rendering. Victory and floor reached are estimated separately. SNIS is primary
because it remains within the observed outcome range and is less exposed to an
unstable empirical weight normalization. OIS remains visible because it has a
different finite-sample bias/variance trade-off and direction disagreement is
useful instability evidence. Neither estimator clips, caps, smooths, or drops
zero-weight trajectories.

Alternative: implement WDR or another doubly robust estimator now. Rejected
because it requires a leakage-safe outcome model and cross-fitting that the
125-trajectory, 1-victory pool cannot validate.

### 3. Bootstrap paired complete trajectories deterministically

The primary uncertainty method is a paired nonparametric bootstrap over whole
trajectory indices. Each replicate samples `n` trajectories with replacement
and recomputes behavior value, SNIS target value, OIS target value, and both
differences. Resampling decisions independently is prohibited.

The production artifact uses 10,000 replicates and a required seed string. Each
draw is derived from SHA-256 of the schema version, seed, replicate index, and
draw index, so output is stable across supported Python versions. The 95%
percentile interval uses sorted exact values with lower index
`floor((B - 1) * 0.025)` and upper index `ceil((B - 1) * 0.975)`. The artifact
records undefined replicate counts, including zero SNIS denominators, and fails
closed if any required primary interval is undefined.

BCa and studentized intervals are deferred. With one observed victory their
jackknife or variance estimates add complexity without creating missing
outcome information.

### 4. Require a separate deterministic calibration artifact

`analysis_scripts.noncombat_ope_calibration` writes a
`noncombat-ope-estimator-calibration-v1` artifact. Estimator validation passes
only when all of these checks pass:

- behavior identity returns exact empirical outcomes for SNIS and OIS;
- balanced one-step and multi-decision synthetic fixtures return their exact
  known target values and preserve trajectory products;
- the hash bootstrap matches complete enumeration on a small fixture;
- input row and trajectory order do not change estimates or intervals;
- a fixed one-step stochastic fixture passes a coverage experiment.

The coverage fixture uses behavior probabilities `(0.5, 0.5)`, target
probabilities `(0.8, 0.2)`, and Bernoulli victory probabilities `(0.2, 0.1)`,
so true target value is `0.18`, behavior value is `0.15`, and difference is
`0.03`. It runs 200 deterministic datasets of 200 trajectories with 500
bootstrap replicates each. The primary SNIS 95% intervals must cover known
target value and known difference in `[0.90, 0.99]` of datasets, and absolute
mean point-estimate bias for each must be at most `0.02`. Full calibration is a
bounded offline artifact, while unit tests use smaller exact fixtures.

Alternative: treat unit arithmetic tests as estimator validation. Rejected
because they do not check interval construction or repeated-sample behavior.

### 5. Separate estimate, comparison, and downstream gates

The estimate artifact exposes independent gates:

- `estimator_validation_ready`: the hash-bound calibration artifact passes;
- `dataset_estimation_ready`: source verification, overlap, terminal outcome,
  and required estimator denominators pass;
- `ope_estimate_ready`: both preceding gates pass and the estimate artifact is
  complete;
- `policy_comparison_ready`: the primary victory comparison additionally has a
  strictly positive 95% SNIS difference lower bound, positive OIS and SNIS
  full-sample differences, and a positive SNIS difference after removing each
  trajectory in turn.

Leave-one-trajectory-out diagnostics report every recomputed point estimate,
undefined case, sign change, and maximum absolute change. Floor-reached results
remain secondary diagnostics and cannot satisfy the primary comparison gate.

Even if all four estimator gates pass, `causal_uplift_ready`,
`formal_noncombat_rl_training_ready`, and `live_policy_promotion_ready` remain
false in this change. A later proposal must define how an accepted comparison
affects policy learning and promotion.

### 6. Independently replay the final artifacts

`analysis_scripts.verify_noncombat_ope_estimates` reparses all inputs and the
calibration/estimate artifacts without importing the main estimator module. It
recomputes exact OIS/SNIS values, deterministic bootstrap draws and quantiles,
leave-one-out diagnostics, hashes, gates, and downstream false invariants.
Tamper tests cover source bytes, calibration results, point estimates,
intervals, and gate booleans.

The B3-B7 proof of concept may produce an OPE estimate when calibration and
dataset gates pass, but it must not claim candidate superiority unless the
pre-specified comparison gates pass. The single observed victory and the
frequency of zero-victory bootstrap replicates remain explicit limitations.

## Risks / Trade-offs

- [One victory can make intervals discrete or uninformative] -> Report the
  bootstrap outcome composition and allow an inconclusive comparison without
  treating it as an estimator failure.
- [SNIS is biased in finite samples] -> Pair it with visible OIS results,
  synthetic bias calibration, ESS diagnostics, and no superiority claim on
  estimator disagreement.
- [Bootstrap intervals can undercover] -> Freeze a known-truth coverage test,
  exact enumeration fixture, and deterministic quantile contract before real
  estimates are accepted.
- [Long trajectory products concentrate weight] -> Reuse exact overlap screens,
  report OIS/SNIS divergence and leave-one-run influence, and never clip after
  seeing results.
- [A correct estimator can be mistaken for a good policy] -> Keep estimator,
  dataset, comparison, causal, training, and promotion gates separate.
- [Offline artifacts could enter production] -> Keep modules under
  `analysis_scripts`, require explicit output paths, and add import/config/
  checkpoint isolation guards.

## Migration Plan

1. Add red tests for exact estimators, bootstrap, calibration, influence, and
   fail-closed artifacts.
2. Implement pure estimator and calibration modules, then the transactional
   CLI and independent verifier.
3. Generate and independently replay the fixed synthetic calibration artifact.
4. Generate B3-B7 estimate artifacts without changing gameplay or collecting
   new runs.
5. Run focused tests, full pytest, OpenSpec strict validation, byte/hash checks,
   and live isolation checks before a cohesive commit.
6. Roll back by deleting the new offline modules, tests, artifacts, and this
   OpenSpec change; existing readiness and gameplay behavior remain intact.

## Open Questions

No implementation question is open. Outcome-model-based estimators, formal RL
reward, training acceptance, and live promotion remain separate future changes.
