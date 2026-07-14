## Context

The known-propensity exploration loop now emits canonical v3 samples whose
behavior distributions, selected-action probabilities, confirmation records,
trajectory groups, and terminal run outcomes can be replayed. B2 contains 230
decision rows from 25 complete runs with card-reward support `174/19` and shop
support `30/7`. All 25 runs lost, so the primary victory outcome is degenerate.

Every decision row repeats its run outcome. Treating those 230 rows as
independent observations would inflate support, while per-decision importance
weights would ignore other randomized decisions in the same run. Existing
policy-pilot code deliberately keeps outcomes diagnostic and does not provide a
target-policy probability or estimator contract. The new capability therefore
belongs in offline analysis code and must not alter production gameplay.

## Goals / Non-Goals

**Goals:**

- Validate one complete, internally consistent trajectory record per AI run.
- Define a versioned terminal-outcome contract without inventing an RL reward.
- Require exact target probabilities over the logged executable support.
- Reconstruct exact trajectory importance weights and deterministic overlap,
  concentration, effective-sample-size, and outcome-variation diagnostics.
- Provide identity-policy and deterministic Current-policy manifest builders as
  auditable plumbing checks.
- Emit fail-closed JSON and Markdown artifacts from B2 while keeping OPE,
  causal, training, and promotion gates false.

**Non-Goals:**

- Estimating policy value, uplift, confidence intervals, or causal effects.
- Selecting, clipping, normalizing, or validating an OPE estimator.
- Defining the formal non-combat RL reward or training a policy.
- Expanding exploration categories or changing behavior-policy rates.
- Modifying live agents, launchers, CommunicationMod configuration, runs, or
  checkpoints.

## Decisions

### 1. Audit at complete-run trajectory granularity

The loader groups samples by `trajectory_group_id`, orders decisions by
`exploration.decision_index`, and requires unique sample and decision ids. Every
row in a trajectory must agree on run file, victory, floor reached, killed-by,
playtime, behavior session, source commit, and trajectory provenance. Missing,
ambiguous, floor-inconsistent, mixed, or conflicting outcomes block the entire
trajectory from readiness accounting and remain listed in diagnostics.

This avoids pseudo-replication. The alternative of treating each decision as an
outcome row was rejected because all decisions in one run share the same
terminal observation and randomized history.

### 2. Keep an outcome contract separate from an RL reward

`noncombat-ope-outcome-contract-v1` fixes the horizon to terminal run completion
and defines two separate channels:

- primary `victory`: an exact boolean Bernoulli outcome;
- secondary `floor_reached`: an exact positive integer progress diagnostic.

The audit does not blend or normalize them. Candidate-policy readiness requires
both victory classes in the audited trajectories; a zero-victory batch reports
`primary_outcome_degenerate`. This contract does not satisfy formal RL reward
readiness because it contains no shaping or optimization objective.

The alternative of combining victory and floor into one scalar was rejected
because any coefficient would encode an unvalidated preference and could mask
the project's actual first-win objective.

### 3. Bind an explicit target distribution to every decision

`noncombat-ope-target-policy-v1` records policy id, optional policy commit,
source sample SHA-256, construction mode, and one entry per sample. Each entry
binds `sample_id`, `state_hash`, behavior `distribution_hash`, and exact target
probabilities for exactly the action ids in the logged executable behavior
distribution. Probabilities are non-negative rational numerator/denominator
pairs that sum exactly to one; zero probability is allowed, mass outside logged
support is not.

Two deterministic builders are in scope:

- `behavior_identity`, which copies the logged behavior distribution and is
  diagnostic-only;
- `current_deterministic`, which assigns probability one to the mapped Current
  baseline action and zero to the other logged executable actions.

Raw Current, Bottled, or model labels are never accepted directly by the audit.
Future adapters must first materialize the complete target manifest, preserving
their provenance and unsupported rows.

### 4. Reconstruct weights exactly, then render bounded diagnostics

For decision `t` in trajectory `i`, the audit computes the exact rational ratio
`r_it = pi(a_it|s_it) / mu(a_it|s_it)`. The trajectory weight is the product of
all ratios in that run. A zero target probability produces an exact zero
trajectory weight. The implementation uses integer-backed `Fraction` values for
validation and products, and adds finite floating representations only for
human-readable metrics.

The report includes trajectory count, decision count, nonzero-weight count,
zero-weight fraction, exact and floating weight rows, sum of weights, effective
sample size `(sum w)^2 / sum(w^2)`, ESS fraction, maximum normalized weight,
category/arm support, and outcome variation. It does not clip, cap, stabilize,
or silently drop weights.

The identity self-check requires every ratio and trajectory weight to equal one,
ESS to equal the trajectory count, and weighted outcome summaries to equal the
unweighted summaries exactly.

### 5. Use conservative overlap screens without authorizing OPE

The versioned readiness policy fixes minimum diagnostic screens at:

- 100 complete trajectories;
- 50 nonzero-weight trajectories;
- trajectory ESS of at least 50;
- ESS fraction of at least 0.5;
- maximum normalized trajectory weight of at most 0.1;
- both primary victory outcomes represented.

These screens reject obviously weak support; they do not validate an estimator.
The artifact has separate `input_valid`, `outcome_contract_ready`,
`target_policy_ready`, `overlap_ready`, `identity_self_check_passed`, and
`estimator_validation_ready` gates. This change always records
`estimator_validation_ready=false`, so `ope_ready`, `causal_uplift_ready`,
`formal_noncombat_rl_training_ready`, and `live_policy_promotion_ready` remain
false even when an identity diagnostic passes.

### 6. Write deterministic, transactional offline artifacts

The CLI accepts canonical sample JSONL, a target manifest or explicit built-in
diagnostic mode, and an output prefix. It validates all inputs before replacing
JSON/Markdown outputs, records source hashes and effective contracts, sorts all
rows and blocker lists deterministically, and uses LF UTF-8 bytes. Invalid JSON,
schema, probability, provenance, or duplicate keys return nonzero without
leaving a partially refreshed artifact pair. Semantically valid but unsupported
data emits a blocked report successfully.

The B2 proof of concept runs both identity and deterministic Current diagnostics.
It must reconstruct exactly 25 trajectories and 230 decisions. Identity weights
must all be one; both reports remain blocked by trajectory count, degenerate
victory, and missing estimator validation.

## Risks / Trade-offs

- [Fixed screening thresholds can be mistaken for statistical sufficiency] ->
  Name them overlap screens, report their values, and keep estimator validation
  and OPE readiness false.
- [Trajectory products can underflow as floats] -> Compute and persist exact
  rational products before producing bounded display floats.
- [A deterministic target can zero many trajectories] -> Preserve zero weights,
  report nonzero support and ESS, and never backfill or clip them.
- [Repeated terminal outcomes can leak across splits] -> Use only trajectory
  groups as independent units and prohibit row-level support claims.
- [B2 has no victories] -> Make primary-outcome variation a blocker rather than
  substituting floor reached as reward truth.
- [Offline tooling could accidentally affect gameplay] -> Keep imports and
  outputs under analysis/test/report paths and verify live isolation hashes in
  the proof-of-concept report.

## Migration Plan

1. Add contracts, validators, target builders, and red/green unit tests.
2. Add deterministic CLI artifact writing and failure-recovery tests.
3. Run identity and Current diagnostics on the frozen B2 samples and freeze the
   blocked proof-of-concept artifacts.
4. Run focused pytest, full pytest, OpenSpec strict validation, and an
   independent artifact replay before commit.
5. Roll back by deleting the offline module, tests, and reports; no production
   configuration, checkpoint, or gameplay migration is required.

## Open Questions

No implementation question is open for this change. Estimator selection,
confidence intervals, target-policy optimization, and promotion thresholds
beyond the overlap screens are deliberately deferred to a later proposal.
