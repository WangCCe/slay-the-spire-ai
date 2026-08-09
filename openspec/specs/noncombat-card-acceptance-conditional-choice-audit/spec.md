# noncombat-card-acceptance-conditional-choice-audit Specification

## Purpose
TBD - created by archiving change audit-card-acceptance-conditional-choice. Update Purpose after archive.
## Requirements
### Requirement: Immutable source-only inputs are independently bound
The audit SHALL consume only the exact tracked 20260808-r2 terminal bundle,
its postmortem, and the canonical 20260809 baseline-support JSON and Markdown.
It SHALL verify the pushed audit source and reused source-only support bytes,
independently verify the terminal/manifest/checkpoint identity, acquire and
hold the inactive execution lease while inventorying and reading every source
artifact, and reject symlinks, reparse points, active or malformed leases,
untracked analytical inputs, source drift, byte drift, or structural drift.
It SHALL NOT import Torch, native/model/runtime/gameplay modules, construct an
environment, access a seed source, or mutate an input.

#### Scenario: Exact consumed evidence is available
- **WHEN** source, prior reports, terminal, manifest, postmortem, checkpoints, chunks, lease, and independent-verifier results match every fixed identity and byte binding
- **THEN** the audit may analyze the already recorded rows under the held inactive lease with all input bindings preserved

#### Scenario: One consumed input differs
- **WHEN** any required path, Git blob, digest, size, schema, identity, inventory row, checkpoint/chunk binding, prior verdict, verifier result, lease state, or canonical byte differs
- **THEN** the audit fails before analytical publication and does not substitute, repair, rediscover, or partially trust evidence

### Requirement: Card-reward distributions and scalar objectives reconstruct exactly
For every chunk, the audit SHALL preserve complete decision and trajectory
order and SHALL recompute family max scores, family softmax, within-family
softmax, joint probabilities, family entropy, each conditional entropy,
expected conditional entropy, selected factorized log probabilities, raw-score
greedy identities, and the five registered scalar objective components from
finite candidate scores and cross-fitted advantages. Reconstructed values SHALL
match the retained diagnostics and chunk ledger under the fixed tolerance. The
eligible card-reward set SHALL contain every multi-family row with `take` and at
least two unique take candidates; rows SHALL NOT be dropped, reordered,
coerced, or deduplicated.

#### Scenario: An eligible card reward is reconstructed
- **WHEN** candidate identities, kinds, scores, selected action, probabilities, advantage, entropies, and chunk denominator are valid
- **THEN** the audit emits one aligned analytical row with exact acceptance and conditional inputs while retaining its trajectory and chunk identity

#### Scenario: Candidate or objective evidence is malformed
- **WHEN** candidates are missing or duplicated, score coverage differs, a value is nonfinite, a probability or entropy does not reconcile, selected or greedy identity differs, a factorized log probability is inconsistent, or a scalar component does not match
- **THEN** the audit rejects the complete input rather than normalizing or omitting the row

### Requirement: Acceptance and conditional pressures use separate fixed coordinates
For each eligible row, the audit SHALL compute direct take-family translation
pressure as
`[A(I_take-p_t) - 0.01 p_t(log(p_t)+H_f) + 0.01 p_t(h_t-H_c)] / N`.
It SHALL also compute, at fixed family mass, each take-candidate conditional
pressure as
`[A I_take(I_selected_j-q_j) - 0.01 p_t q_j(log(q_j)+h_t)] / N`.
For one unique score-greedy take candidate, conditional margin pressure SHALL be
that candidate's pressure minus the arithmetic mean pressure of all other take
candidates. Positive values SHALL mean gradient descent directly raises the
named row-local coordinate before shared-parameter effects. The audit SHALL
keep policy and entropy contributions separately observable.

#### Scenario: A take family is translated uniformly
- **WHEN** the same finite score delta is applied to every take candidate while non-take scores remain fixed
- **THEN** acceptance inputs change as reconstructed while within-take probabilities, entropy, ordering, and gaps remain unchanged

#### Scenario: Conditional choice changes at fixed family max
- **WHEN** nonmax take scores are redistributed without changing the take-family maximum
- **THEN** family mass remains unchanged while conditional probabilities, entropy, gaps, and conditional pressure may change

#### Scenario: A max take score is perturbed
- **WHEN** a perturbation changes both the take-family maximum and its within-family distribution
- **THEN** the audit reports the coupled boundary and does not claim that the two counterfactual coordinates sum to the actual shared update

#### Scenario: The greedy take action is tied
- **WHEN** multiple take candidates share the maximum raw score
- **THEN** the row remains counted and its tie identities are preserved, but no unique conditional margin pressure is reported or imputed

### Requirement: Threshold-free chunk trends classify bounded mechanism evidence
The audit SHALL report all eight chunk summaries and fixed early `0..3` and
final `4..7` windows. Every supported chunk SHALL contain at least 64 eligible
rows, at least 64 rows with one unique score-greedy take candidate, at least 16
selected take rows, and at least 16 selected non-take rows. Individual tied
rows SHALL remain eligible and counted but SHALL omit conditional margin rather
than being imputed. The audit SHALL
report take-candidate multiplicity, normalized take entropy `h_t/log(K)`,
maximum conditional probability, top-two probability gap, selection and greedy
counts, ties, acceptance pressure, and conditional margin pressure.

`conditional_concentration_progresses` SHALL be true only when mean normalized
take entropy strictly decreases and mean top-two gap strictly increases across
all seven adjacent chunk boundaries. `acceptance_pressure_consistent` SHALL be
true only when aggregate acceptance pressure is positive in every chunk.
`conditional_pressure_consistent` SHALL be true only when aggregate conditional
margin pressure is positive in every final-window chunk.

#### Scenario: Acceptance and conditional pressure are both consistent
- **WHEN** support passes, acceptance pressure is positive in all chunks, both conditional concentration trends are monotonic, and conditional margin pressure is positive in chunks `4..7`
- **THEN** the verdict is `acceptance_and_conditional_pressure_consistently_aligned`

#### Scenario: Concentration progresses with mixed direct conditional pressure
- **WHEN** support passes, acceptance pressure is positive in all chunks, both conditional concentration trends are monotonic, and any final-window conditional margin pressure is nonpositive
- **THEN** the verdict is `acceptance_pressure_with_conditional_concentration_but_mixed_direct_pressure`

#### Scenario: Acceptance is consistent without monotonic concentration
- **WHEN** support passes and acceptance pressure is positive in all chunks but either conditional concentration trend is not monotonic
- **THEN** the verdict is `acceptance_pressure_without_monotonic_conditional_concentration`

#### Scenario: Acceptance pressure is not consistent
- **WHEN** support passes but any chunk aggregate acceptance pressure is nonpositive
- **THEN** the verdict is `acceptance_pressure_not_consistent`

#### Scenario: Required support is absent
- **WHEN** exact reconstruction passes but any per-chunk eligible-row, unique-greedy-row, or selected-side support minimum is absent
- **THEN** the verdict is `insufficient_support_or_evidence` without merging chunks or tuning a threshold

### Requirement: Shared-parameter gradients remain exact but non-causal
The audit SHALL decode every bound float64 component and full-gradient vector
with standard-library code, verify dtype, shape, byte order, data digest,
component order, scalar/full reconstruction, uniform clipping, and finite
values, and report per-chunk norms, pairwise dots, and cosines for family,
conditional, entropy, other-policy, and full gradients. It SHALL NOT interpret
parameter-space geometry as a per-row candidate-score derivative because the
bundle contains no per-row score Jacobian or counterfactual update.

#### Scenario: Shared gradient components reconstruct
- **WHEN** all component vectors and the independently retained full vector are valid
- **THEN** their exact geometry and bounded reconstruction residuals are published separately from score-space pressure

#### Scenario: A candidate-effect claim is requested
- **WHEN** family or conditional parameter gradients align with the full gradient or with each other
- **THEN** the report preserves that observation but rejects causal attribution to acceptance, one card choice, or the observed concentration trend

### Requirement: Deterministic publication grants no downstream authority
The audit SHALL render one compact canonical JSON report and one Markdown
summary from a pushed source identity. Two fresh isolated source-only processes
using separate staging paths SHALL produce byte-identical outputs. The report
SHALL bind exact source/input identities, verifier results, exploratory-probe
disclosure, complete reconstruction counts, chunk trends, pressure components,
gradient geometry, verdict inputs, limitations, and an exact all-false
authority map. It SHALL contain no unrestricted decision dump or raw gradient
vector.

#### Scenario: Publication succeeds
- **WHEN** identity, reconstruction, support, synthetic, trend, gradient, import-isolation, determinism, and report-size gates pass
- **THEN** the reports may be published without modifying consumed evidence or granting execution, replay, seed access, fitting, training, evaluation, OPE, model/native loading, gameplay, CommunicationMod, formal-RL, qualification, promotion, policy-quality, or causal authority

#### Scenario: A downstream change or run is requested
- **WHEN** any verdict is cited as authority for an objective, coefficient, architecture, checkpoint, cohort, experiment, evaluation, or live policy
- **THEN** the request remains blocked pending a separate reviewed proposal and any required execution authorization
