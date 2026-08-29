## Why

The augmented real-context corpus now passes every registered support gate,
while the fixed unweighted expanded item-semantic fit still fails fresh
evaluation with precision `0.339623`, mean selected advantage `-0.055328`,
regret `2.97746`, and 59 severe harms. The smallest training experiment that
uses the new evidence is one fixed real-context-weighted fit, not another
architecture, threshold sweep, corpus search, or live-policy attempt.

## What Changes

- Bind the exact support-passing train corpus, augmented fresh evaluation
  corpus, r14/r15 real replay target, context-cell definition, and published
  support report into one source-committed training registration.
- Split the bound training rows deterministically by source-seed parity: even
  seeds for fitting and odd seeds for calibration. Keep the entire augmented
  fresh evaluation partition inaccessible until fitting and calibration are
  frozen.
- Reuse the existing item-semantic three-class architecture, labels, optimizer,
  4,096-update budget, per-class sample count, ranking loss, and 95th-percentile
  negative calibration rule; change only class-balanced pair sampling, ranking
  sampling, and calibration to honor exact real-context weights.
- Report both raw and real-context-weighted fresh metrics. Apply the existing
  precision, selected-advantage, and regret thresholds to weighted metrics,
  while retaining raw minimum-intervention and zero severe, illegal, and
  forbidden-selection safety gates.
- Execute at most one CPU fit per registered execution with no sweep, retry
  after policy-metric access, native loading, Slay the Spire, CommunicationMod,
  production-checkpoint mutation, or promotion. One corrective successor ID is
  permitted only when a committed failure report proves the predecessor
  produced no policy metric or output and the fix changes no evidence, recipe,
  seed, weight, threshold, or gate. A passing result may only authorize a
  separately registered fresh matched LightSTS policy gate.

Success means one immutable artifact passes all raw safety and weighted fresh
offline gates. A completed policy decision closes this exact recipe without
changing seeds, weights, thresholds, architecture, optimizer, or update count.
No current live
evidence is changed or superseded; production r16 remains the rollback boundary
and the new artifact is development-only.

## Capabilities

### New Capabilities

- `combat-rl-real-context-weighted-action-relative-fit`: Deterministic
  context-weighted fit, calibration, fresh evaluation, provenance, and
  fail-closed authority for the action-relative item-semantic classifier.

### Modified Capabilities

None.

## Impact

The change adds one compact offline training runner, focused tests, a
source-only registration, and immutable fit/report artifacts. It reuses the
existing balanced-corpus weighting helpers, action-relative item-semantic
classifier, production-r16 frozen parent, and existing offline gate thresholds.
It changes no runtime API, gameplay policy, CommunicationMod configuration,
simulator mechanics, action space, reward, production checkpoint, or live
promotion state.
