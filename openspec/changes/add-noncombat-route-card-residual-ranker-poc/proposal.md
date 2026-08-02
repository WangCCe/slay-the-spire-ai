## Why

The completed structured-ranker POC was a deterministic negative because its
event and shop heads collapsed, but it exposed stable route gains and smaller,
mixed card-reward gains over the legacy control. One terminal train-only POC is
needed to test whether those signals survive as bounded corrections to the
legacy scorer without replacing its stronger behavior or spending fresh
simulator evidence.

## What Changes

- Add one offline-only route/card residual-ranker POC over the same preserved
  warm-start train demonstrations (`4000..4031`), with no access to validation
  or final cohorts and no native simulator use.
- Train one frozen legacy base per seed-grouped fold, then fit exactly one
  zero-initialized bounded residual for route and card-reward choices only.
  Event and shop scores, probabilities, predictions, and tie behavior remain
  byte-identical to the legacy control.
- Materialize aggregate, category, and per-fold agreement and cross-entropy
  metrics, base-delegation proofs, residual-magnitude diagnostics, model
  identities, held-out predictions, and deterministic replay in the canonical
  artifact set.
- Apply one preregistered terminal gate: route and card-reward must each avoid
  agreement and cross-entropy regression in every fold, improve in aggregate,
  event/shop delegation must be exact, and overall macro agreement and cross
  entropy must improve without post-result retry.
- Stop baseline-imitation model trials if the candidate fails. A positive
  result may authorize only a separate fresh-study proposal; it grants no
  simulator, live, formal-RL, qualification, or promotion authority.

No live evidence is collected or changed. The motivating evidence is the
hash-closed structured-ranker negative result and its read-only failure audit.
POC success means deterministic held-out implementation-fit improvement on the
already observed corpus under the fixed gate; it is not a policy-quality claim.

## Capabilities

### New Capabilities

- `noncombat-route-card-residual-ranker`: Defines the frozen legacy base,
  route/card-only bounded residual, exact event/shop delegation, seed-grouped
  terminal gate, canonical per-fold reporting, and no-authority verdicts.

### Modified Capabilities

None.

## Impact

- Adds a dedicated offline analysis surface under `analysis_scripts/`, focused
  tests, one immutable train-only registration, and generated reports.
- Reads the existing canonical train-only input and structured-ranker result as
  bound evidence without modifying either artifact.
- Changes no live agent behavior, CommunicationMod configuration, checkpoint
  discovery, external simulator checkout, production dependency, or formal-RL
  path. Rollback is deletion of only the new POC code, tests, OpenSpec
  artifacts, registration, and reports.
