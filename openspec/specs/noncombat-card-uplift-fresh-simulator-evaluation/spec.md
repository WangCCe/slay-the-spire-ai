# noncombat-card-uplift-fresh-simulator-evaluation Specification

## Purpose
TBD - created by archiving change add-card-uplift-fresh-simulator-evaluation. Update Purpose after archive.
## Requirements
### Requirement: Registration binds frozen inputs and an untouched cohort
The evaluator SHALL bind the tracked source commit, native module identity, r7
entry checkpoint, residual model, predecessor train/development/audit evidence,
the consumed failed r1 seeds `90000..90063`, replacement seeds `90100..90163`,
interpreter, limits, gates, output, and authority before
constructing an environment. The cohort MUST be disjoint from every seed used
to fit, select, develop, or audit the residual.

#### Scenario: A bound input drifts
- **WHEN** preflight finds a hash, path, source, native identity, schedule,
  limit, gate, or authority mismatch
- **THEN** it fails before constructing any simulator environment or consuming
  any fresh seed

### Requirement: Evaluation uses paired independent whole-run rollouts
The evaluator SHALL run one native control and one frozen candidate episode in
independent environments for each registered seed. Control SHALL use the native
baseline at every decision. Candidate SHALL use the frozen r7-plus-residual
ranking only at supported card rewards and native baseline at every other
decision.

#### Scenario: Candidate reaches a supported card reward
- **WHEN** the candidate state exposes exactly three legal `take` actions and
  one legal `skip` action
- **THEN** it deterministically selects the highest composed score, records the
  same-state native choice from a disposable clone, and applies only the legal
  candidate action to the candidate environment

#### Scenario: Either arm reaches a registered support blocker
- **WHEN** a rollout reaches a registered native support blocker
- **THEN** the seed pair is censored without replacement and its reason is
  recorded

### Requirement: Result reports paired trajectory and intervention evidence
The result SHALL include per-arm trajectories, terminal floor, victory,
decision/category counts, card choices, action legality, censors, paired floor
differences, victory counts, intervention counts, and a deterministic
10,000-resample 95 percent percentile-bootstrap interval using seed `20260813`.

#### Scenario: Complete evidence is aggregated
- **WHEN** all registered seeds have either a complete pair or a registered
  censor
- **THEN** aggregate metrics are computed only from complete pairs and every
  retained row remains traceable to its seed and action sequence

### Requirement: Fixed gates control the next step
The evaluator SHALL pass only with at least 56 complete pairs, at most eight
registered censored pairs, at least 12 candidate card interventions,
nonnegative mean paired terminal-floor difference, bootstrap lower bound at
least `-2.0`, candidate victories no lower than control, legal actions, and
unchanged source/model bytes.

#### Scenario: Every fixed gate passes
- **WHEN** all structural, resource, support, intervention, floor,
  noninferiority, victory, and immutability gates pass
- **THEN** the verdict authorizes only a separate thin live shadow-adapter
  proposal

#### Scenario: A fixed gate fails
- **WHEN** any fixed gate fails after fresh access
- **THEN** the result is published as not ready and the cohort MUST NOT be
  retried, replaced, tuned against, or relabeled as fresh evidence

### Requirement: Runtime remains isolated from production
The evaluator SHALL run on CPU with at most 64 paired seeds, 128 complete
episode rollouts, 10,000 bootstrap resamples, and 7,200 seconds wall-clock. It
MUST NOT fit or train a model, start the game or CommunicationMod, load or
modify a production checkpoint, perform OPE, or promote a policy.

#### Scenario: Evaluation completes or stops
- **WHEN** execution publishes a result or reaches a resource or infrastructure
  stop
- **THEN** production behavior and checkpoints remain unchanged and authority
  for training, gameplay, qualification, causal claims, and promotion remains
  false
