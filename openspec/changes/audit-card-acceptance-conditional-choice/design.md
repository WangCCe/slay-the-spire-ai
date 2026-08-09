## Context

The consumed 20260808-r2 successor stores eight canonical gzip chunk artifacts
covering 512 trajectories and 11,729 decisions. Every decision retains
candidate identity, kind, raw score, family/conditional/joint probability,
selected action and family, score-greedy action and family, cross-fitted
advantage, and factorized objective terms. Each chunk also retains the five
named shared-parameter gradient vectors, full gradient, clipping evidence, and
scalar components. The existing independent verifier and baseline-support
audit already validate the terminal identity and direct take-family pressure.

The published baseline audit answers whether lower-bound baseline clipping is
sufficient to explain take-family pressure. It does not answer whether the
policy is primarily moving toward accepting any card, becoming more
concentrated within the offered cards, or exhibiting both through shared
parameters. The exploratory probe used to scope this change was read-only and
looked at the known r2 rows, so the new publication is a deterministic
descriptive audit rather than a blind preregistration or causal test.

## Goals / Non-Goals

**Goals:**

- Reverify the immutable r2 bundle and prior audit under one inactive lease.
- Reconstruct all candidate probabilities and objective scalars from raw rows.
- Separate a take-family translation coordinate from a fixed-family-mass
  within-take conditional coordinate.
- Preserve complete per-chunk trends, fixed support checks, shared-gradient
  geometry, ties, and the limitation between score-space and parameter-space
  evidence.
- Publish one threshold-free bounded verdict and byte-identical JSON/Markdown
  from fresh source-only processes.

**Non-Goals:**

- Infer card value, policy value, causal effects, independent-row uncertainty,
  OPE, or live-game impact.
- Select or change a reward, coefficient, objective, ranker, architecture,
  optimizer, checkpoint, seed, cohort, policy, or saturation threshold.
- Import Torch or production modules, load model/native state, construct an
  environment, access or replay seeds, fit, train, evaluate, qualify, promote,
  or launch CommunicationMod.

## Decisions

### Bind the existing evidence rather than reconstructing an experiment

The audit will bind the exact terminal, manifest, postmortem, prior baseline-
support JSON/Markdown, eight checkpoint documents, and eight chunk-evidence
bindings. It will reuse the checked-in standard-library terminal verifier and
source-only parsing/lease helpers from the baseline-support audit while
independently reconstructing the new metrics. The reused source files and prior
report bytes are explicit input bindings. All terminal files are inventoried
and read only while the inactive execution lease is held.

Alternative: load the final model and rescore rows. Rejected because it adds
model/runtime authority and can silently diverge from the exact pre-update
scores that produced each recorded action.

### Reconstruct the two score-space coordinates analytically

For each eligible card reward, let `A` be the cross-fitted advantage, `N` the
complete chunk decision count, `p_t` the take-family probability, `H_f` family
entropy, `q_j` take-conditional probabilities, `h_t` take entropy, `H_c`
expected conditional entropy, and both registered entropy coefficients equal
`0.01`.

The acceptance coordinate translates every take-candidate score by the same
amount. Its gradient-descent pressure is the existing exact direct take-family
pressure:

`[A(I_take-p_t) - 0.01 p_t(log(p_t)+H_f) + 0.01 p_t(h_t-H_c)] / N`.

This translation leaves `q_j`, take entropy, and within-take gaps unchanged.

The conditional coordinate freezes family mass and reconstructs one pressure
per take candidate:

`[A I_take(I_selected_j-q_j) - 0.01 p_t q_j(log(q_j)+h_t)] / N`.

For a unique current score-greedy take candidate `g`, the conditional margin
pressure is its pressure minus the arithmetic mean pressure of the remaining
take candidates. Positive pressure widens that row-local greedy-versus-peer
margin under gradient descent. A take tie has no margin value and remains an
explicit unsupported row.

Alternative: differentiate a loaded Torch graph. Rejected because the retained
scores and exact analytical factorization are sufficient, while Torch import
would weaken source isolation. Alternative: treat the selected action as the
collapse target. Rejected because stochastic selection can differ from the
current greedy action and would answer a different question.

### Use exact trends and signs instead of a learned magnitude threshold

Every chunk must contain at least 64 eligible rows, at least 64 rows with one
unique score-greedy take candidate, and at least 16 recorded take and 16
recorded non-take selections. Individual take ties remain eligible and counted
but do not receive a conditional margin value. The audit reports take-candidate multiplicity,
normalized take entropy `h_t/log(K)`, maximum take-conditional probability,
top-two conditional probability gap, acceptance pressure, conditional margin
pressure, selection counts, and ties.

`conditional_concentration_progresses` is true only when mean normalized take
entropy strictly decreases and mean top-two gap strictly increases across all
seven adjacent chunk boundaries. `acceptance_pressure_consistent` is true only
when aggregate acceptance pressure is positive in every chunk.
`conditional_pressure_consistent` is true only when aggregate conditional
margin pressure is positive in each registered final-window chunk `4..7`.

The verdict follows this fixed decision order:

1. Missing identity, malformed structure, or failed arithmetic reconstruction
   aborts publication without a verdict.
2. A per-chunk eligible-row, unique-greedy-row, or selected-side support
   minimum failure yields `insufficient_support_or_evidence`; individual ties
   remain counted and omit only their margin value.
3. Nonpositive acceptance pressure in any chunk yields
   `acceptance_pressure_not_consistent`.
4. Consistent acceptance without monotonic conditional concentration yields
   `acceptance_pressure_without_monotonic_conditional_concentration`.
5. Consistent acceptance, monotonic concentration, and positive conditional
   pressure in every final chunk yields
   `acceptance_and_conditional_pressure_consistently_aligned`.
6. Otherwise it yields
   `acceptance_pressure_with_conditional_concentration_but_mixed_direct_pressure`.

This decision tree intentionally distinguishes observed concentration from the
direct score-space component that might produce it.

### Preserve shared-gradient geometry as a limitation, not an attribution

The audit decodes each float64 component vector with only standard-library
base64, SHA-256, and `array`. It verifies shape/order, scalar reconciliation,
component-sum/full-gradient reconstruction, clip factor, and publishes norms,
dots, and cosines for family policy, conditional policy, entropy components,
and the full gradient. These vectors share ranker parameters, but the bundle
does not retain per-row score Jacobians. Therefore the audit cannot map a
parameter-space component to a particular candidate margin or explain a trend
causally.

### Prove the coordinate boundary with synthetic fixtures

Fixed pure-Python fixtures cover: uniform take-score translation with unchanged
conditional probabilities; nonmax within-take redistribution with unchanged
family max and changed conditional probabilities; max-score perturbation that
changes both coordinates; selected/nonselected take actions; entropy pressure;
ties; extreme finite scores; and malformed candidates. The audit remains absent
when existing runtime, agent, ranker, or production modules are imported.

### Publish only after a pushed source boundary

The complete plan is committed and pushed before implementation. The source
and tests are then committed and pushed before publication. Two fresh isolated
processes use separate staging directories and the pushed source identity;
their JSON and Markdown bytes must match. The canonical pair is then committed
with project direction, the OpenSpec delta is synced and archived, and the
configured focused, `commit`, `full`, strict OpenSpec, diff, and review gates
close the change.

## Risks / Trade-offs

- [Risk] The exploratory probe influenced metric choice. -> Disclose it,
  prohibit tuned magnitude thresholds, retain the complete chunk series, and
  use exact sign/monotonic predicates only.
- [Risk] Max pooling couples family and conditional score effects. -> Define
  explicit counterfactual coordinates, add the coupled synthetic fixture, and
  never claim they sum to the actual shared update.
- [Risk] Repeated decisions are correlated within trajectories. -> Publish
  counts and descriptive aggregates without confidence intervals or
  independent-row claims.
- [Risk] Standard-library vector decoding is slow or large. -> Enforce the
  existing 64 MiB stored/canonical chunk bounds, exact vector shapes and
  digests, and no unrestricted row dump in the report.
- [Risk] A later result is used to justify training. -> Keep every authority
  false and require a separate reviewed algorithm or empirical proposal.

## Migration Plan

1. Commit and push the complete OpenSpec planning boundary.
2. Add RED synthetic, identity, arithmetic, malformed-input, verdict,
   determinism, and import-isolation regressions.
3. Implement the standard-library audit and pass focused tests.
4. Commit and push source before reading the sealed bundle for publication.
5. Run two isolated audits, compare bytes, and publish the canonical pair.
6. Run focused, `commit`, `full`, strict OpenSpec, diff, and independent review
   gates; update direction; sync and archive the change; commit and push.

Rollback removes the new source, tests, reports, specification, archived
change, and direction entry. No r2, baseline-audit, checkpoint, policy, gate,
or live configuration artifact is modified.

## Open Questions

None.
