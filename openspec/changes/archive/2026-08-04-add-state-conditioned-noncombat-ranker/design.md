## Context

The r2 runner encodes each legal candidate as the sum of one shared state vector
and one candidate vector, then applies `CandidateRanker`, a single affine scalar
layer. For candidates `i` and `j`, the score difference is therefore independent
of the shared state vector. The terminal postmortem binds the source and result:
the trained policy improved floor progress against seeded initialization, but
had no victories, never reached floor 51, and selected `take` for every observed
evaluation card reward.

The repository already has a bounded warm-start POC that uses one hidden ReLU
layer because a purely additive scorer cannot represent state-dependent
thresholds. That architecture is useful precedent, but its private class and
teacher-study lifecycle are not a reusable simulator-RL boundary.

The completed r2 verifier binds six implementation files by hash. Editing those
files would make a current-checkout verification of historical evidence drift,
so this change must be additive.

## Goals / Non-Goals

**Goals:**

- Add a small versioned scorer whose candidate ordering can depend on shared
  state and candidate identity.
- Make state and candidate tensors explicit at the API boundary rather than
  summing them before scoring.
- Prove deterministic CPU behavior, legal candidate alignment, finite values,
  candidate-order equivariance, and state-dict round trips.
- Produce deterministic, standard-library anti-collapse summaries from
  decision rows containing complete candidates, selections, and score maps.
- Keep historical r2 artifacts and their bound implementation verifiable.

**Non-Goals:**

- No training, warm start, hyperparameter comparison, r3 registration, seed or
  environment access, native adapter load, or experiment execution.
- No reward, REINFORCE, optimizer, baseline, threshold, or cohort change.
- No Current, Bottled, SimpleAgent, CommunicationMod, live gameplay, checkpoint,
  model-loading, formal-RL, qualification, or promotion integration.
- No migration or reinterpretation of the linear v1 ranker or r1/r2 evidence.

## Decisions

### Add a versioned one-hidden-layer ranker

Create `StateConditionedCandidateRanker` in a new development-only ranker module. It
accepts one state feature vector and a matrix of candidate feature vectors,
concatenates the repeated state vector with each candidate row, applies one
fixed-width affine layer, ReLU, and a scalar output layer. The architecture has
no dropout, batch normalization, recurrent state, or implicit device transfer.

The model is intentionally the same capacity class used by the bounded
warm-start POC, but is a separate reusable type with its own architecture id.
The hidden width is explicit constructor metadata and defaults to 64; a future
experiment must preregister its exact value and model seed.

Alternative: add a bilinear two-tower scorer. This makes interaction explicit,
but introduces a new architecture without existing repository evidence.

Alternative: keep a linear scorer and add hand-authored interaction features.
The structured baseline POC already does this for known semantics, but it would
make the generic policy dependent on an incomplete manual interaction catalog.

### Keep state and candidate tensors separate

The forward boundary receives a one-dimensional state tensor and a
two-dimensional candidate tensor with the same feature width. It validates CPU
placement, floating dtype, finite values, nonempty candidates, and exact shapes.
It never creates, removes, masks, reorders, or silently casts candidates.

The nonlinearity follows concatenation. Consequently, shared state can move
hidden-unit activation boundaries differently for different candidates. A
regression configures a two-unit network to prefer candidate A in one state and
candidate B in another while candidate tensors remain byte-identical.

Alternative: concatenate and use one linear output. Rejected because shared
state would still cancel from pairwise score differences.

### Keep historical implementation immutable

Do not edit `analysis_scripts/noncombat_policy_model.py`,
`analysis_scripts/noncombat_simulator_rl_experiment.py`, the r2 verifier, or the
r2 runner. The new module can be evaluated independently and a later experiment
can opt into it under a fresh source identity. The existing r2 verifier remains
a required regression gate.

### Make anti-collapse reporting descriptive and authority-free

Add a separate standard-library-only diagnostic module so read-only reporting
does not import Torch. Its summarizer consumes normalized decision records with:

- stable decision id and category;
- complete candidate records with unique action id and nonempty kind;
- one selected action id; and
- a finite score mapped to every candidate action id.

For each category it reports decision count, candidate-kind opportunity count,
selected-kind count and rate, distinct selected kinds, top-score and selected
score-margin distributions, single-candidate count, and exact single-kind
saturation. Card rewards also report take/skip/bowl availability and selection
counts from candidate kind. Results are canonical and independent of input row
or candidate ordering.

These fields are diagnostics only. This change adds no numerical pass threshold
and no experiment or promotion verdict.

## Risks / Trade-offs

- **A state-sensitive model can still learn a collapsed policy** -> Require
  complete candidate opportunity and selection-rate diagnostics; do not infer
  competence from architecture alone.
- **The MLP adds parameters and may overfit** -> Keep one bounded hidden layer,
  deterministic CPU execution, and defer training design to a fresh proposal.
- **Generic hashed inputs may still be weak** -> This change proves capacity at
  the tensor boundary only; a later experiment must bind its leakage-controlled
  projection and feature diagnostics.
- **Changing historical source would invalidate current-checkout verification**
  -> Add new files only and run the existing r2 independent verifier unchanged.
- **Score margins can be misread as confidence** -> Label them as raw descriptive
  logits and grant no calibration or policy-quality authority.

## Migration Plan

1. Add red state-sensitivity and diagnostic-contract tests.
2. Add the new versioned module without modifying v1 or r2 files.
3. Run focused tests, the repository commit gate, strict OpenSpec validation,
   and the historical r2 verifier.
4. Publish no model or execution artifact under this change.

Rollback deletes the new module, focused tests, and this change. Existing
imports, models, artifacts, and production behavior remain unchanged.

## Open Questions

The credible fixed comparator, feature projection, training algorithm, reward
use, fresh cohort, and success thresholds for a future experiment remain open.
They must be resolved and preregistered in a separate change after this
state-conditioning boundary verifies.
