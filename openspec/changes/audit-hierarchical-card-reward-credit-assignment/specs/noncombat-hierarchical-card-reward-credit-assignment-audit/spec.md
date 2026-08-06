## ADDED Requirements

### Requirement: Immutable verified terminal inputs
The audit SHALL consume only the tracked terminal evidence for
`noncombat-hierarchical-simulator-learning-20260806-r1`. It SHALL bind and
verify the terminal artifact manifest, registration, authorization, training
rows, checkpoints, execution journal, metrics, isolation result, terminal
verdict, postmortem, and exact audit source identity before analysis. The audit
source worktree bytes SHALL match the `HEAD` blob at the fixed source path; a
self-reported source digest alone is insufficient. The existing untracked
`.execution.lease` SHALL be the sole non-analytical control-file exception: the
audit SHALL first acquire a non-blocking exclusive lock, validate its canonical
execution identity while locked, and retain that lock without modifying its
bytes while snapshotting and analyzing the otherwise tracked terminal bundle.

#### Scenario: Every input matches
- **WHEN** every required path, canonical byte sequence, digest, size, schema, logical identity, and manifest relationship matches the tracked terminal bundle
- **THEN** the audit may analyze the already recorded training decisions without importing Torch, loading native code or a model, constructing an environment, or accessing a seed

#### Scenario: A consumed artifact differs
- **WHEN** any required analytical input is missing, noncanonical, untracked, hash-mismatched, identity-mismatched, incomplete, or inconsistent with the verified saturation verdict, or the sole permitted lease control is missing, malformed, mismatched, modified, or actively locked
- **THEN** the audit fails closed before publishing analytical metrics or a verdict

### Requirement: Exact registered trajectory reconstruction
The audit SHALL reconstruct each contiguous training chunk, episode, decision
order, reward to go, float32-normalized return, selected family probability,
family entropy, per-family and expected conditional entropy, raw-score maximum
family, and family score margin from the canonical training rows. Its
reconstructed chunk objective summaries SHALL match the terminal checkpoint
summaries under the registered arithmetic and existing verifier tolerance.

#### Scenario: Recorded training rows are valid
- **WHEN** all eight chunks and their seed-grouped decisions reproduce the registered reward-to-go and normalized-return arithmetic
- **THEN** the audit emits one aligned analytical row per recorded decision and exact aggregate reconciliation evidence

#### Scenario: Order or arithmetic drifts
- **WHEN** a chunk, seed, decision index, reward, selected family, probability, entropy, score maximum, margin, normalization branch, or reconstructed objective differs
- **THEN** the audit rejects the input rather than sorting away, coercing, imputing, or tolerating the drift

### Requirement: Direct family-logit objective pressure
For each multi-family card-reward decision, the audit SHALL compute the direct
registered take-family logit update pressure as
`[A * (I_take - p_take) - 0.01 * p_take * (log(p_take) + H_family) + 0.01 * p_take * (h_take - H_cond)] / N`,
where `A` is the exact normalized return, `I_take` indicates that `take` was
selected, `p_take` is its recorded family probability, `H_family` is recorded
family entropy, `h_take` is reconstructed take-family conditional entropy,
`H_cond` is verified expected conditional entropy, and `N` is the total number
of decisions in that training chunk. Positive pressure SHALL mean that gradient
descent directly raises the row-local take family logit before shared-parameter
effects.

#### Scenario: Direct pressure is reconstructed
- **WHEN** a multi-family card reward contains valid take probability, selected family, entropy, and normalized return
- **THEN** the audit reports separate policy, family-entropy, expected-conditional-entropy, and combined take-logit pressures with sign, sum, mean, and selected-family counts

#### Scenario: A full-gradient claim is requested
- **WHEN** the report interprets direct logit pressure in the presence of shared ranker parameters or the conditional objective
- **THEN** it explicitly rejects equivalence to the full model-parameter gradient, causal card value, or an intervention effect

### Requirement: Fixed descriptive confounding strata
The audit SHALL report card-reward return, propensity, score-margin, entropy,
and direct-pressure summaries by chunk; pre-decision effective-floor bands
`<17`, `17..33`, and `>=34`; card-reward ordinals `first`, `second`, and
`later`; take-propensity bands `[0,0.50)`, `[0.50,0.51)`, `[0.51,0.52)`, and
`[0.52,1]`; and family-score-margin bands `[0,0.025)`, `[0.025,0.05)`,
`[0.05,0.075)`, and `[0.075,+inf)`. It SHALL also report one seed-cluster row
per consumed training seed. The complete eligible set SHALL contain at least 64
rows and at least 16 recorded selections each for `take` and `skip`, and each
non-chunk banding dimension SHALL contain at least one supported band. Chunk
summaries are mandatory alignment checks but SHALL NOT count as non-chunk
heterogeneity strata.

#### Scenario: A stratum has descriptive overlap
- **WHEN** a fixed stratum contains at least 64 eligible rows and at least 16 recorded selections each for `take` and `skip`
- **THEN** the audit marks it supported and reports both selected-family outcome associations plus aggregate direct pressure

#### Scenario: A stratum is sparse or one-sided
- **WHEN** a fixed stratum misses either support threshold
- **THEN** the audit preserves its raw counts and labels it insufficient without merging bands, changing thresholds, or extrapolating an effect

#### Scenario: Repeated decisions share a run
- **WHEN** one seed contributes multiple card-reward decisions
- **THEN** the audit preserves decision-level rows but reports seed-cluster counts and aggregates separately and makes no independent-row confidence claim

### Requirement: Bounded descriptive verdict
The audit SHALL classify only the relationship between recorded direct
take-logit pressure, observed greedy take-margin growth, and fixed supported
strata. It SHALL use one of
`direct_take_pressure_consistently_aligned`,
`direct_take_pressure_aligned_but_stratum_heterogeneous`,
`direct_take_pressure_not_aligned`, or
`insufficient_overlap_or_evidence`.
Input, identity, order, or arithmetic reconstruction failure SHALL abort
publication without analytical metrics or a verdict. For a valid
reconstruction, the terminal window SHALL be exactly chunks 4 through 7 and
its mean take-family margin SHALL count as growing only if every adjacent chunk
mean is strictly larger than its predecessor.

#### Scenario: Aggregate alignment has supported heterogeneity
- **WHEN** every training chunk has positive aggregate combined take-logit pressure and the terminal-window mean take margin grows, but any supported non-chunk fixed stratum has nonpositive aggregate pressure
- **THEN** the verdict is `direct_take_pressure_aligned_but_stratum_heterogeneous`

#### Scenario: Alignment is consistent
- **WHEN** every training chunk and every supported non-chunk fixed stratum has positive aggregate combined pressure and the terminal-window mean take margin grows
- **THEN** the verdict is `direct_take_pressure_consistently_aligned`

#### Scenario: Aggregate pressure is not aligned
- **WHEN** any training chunk has nonpositive aggregate combined pressure or the terminal-window mean take margin does not grow
- **THEN** the verdict is `direct_take_pressure_not_aligned`

#### Scenario: Evidence support fails
- **WHEN** exact reconstruction is valid but the fixed global take/skip overlap or per-dimension supported-band minimum is absent
- **THEN** the verdict is `insufficient_overlap_or_evidence`

### Requirement: Canonical publication with no downstream authority
The audit SHALL publish a canonical machine-readable report, a bounded human
summary, and exact source/input bindings. The report SHALL remain byte-stable
across fresh source-only processes and SHALL keep every execution, replay,
training, OPE, causal, model-loading, gameplay, qualification, formal-RL,
target-supported-outcome, and promotion authority false.

#### Scenario: Audit publication succeeds
- **WHEN** all input, reconstruction, pressure, stratum, verdict, determinism, and import-isolation checks pass
- **THEN** fresh source-only runs publish byte-identical reports without modifying any consumed artifact

#### Scenario: The verdict appears mechanism-consistent
- **WHEN** direct pressure is aligned with greedy-margin growth under any bounded verdict
- **THEN** the report permits only a separately reviewed algorithm-proposal discussion and does not authorize a coefficient, reward, advantage, architecture, checkpoint, seed, experiment, or live-policy change
