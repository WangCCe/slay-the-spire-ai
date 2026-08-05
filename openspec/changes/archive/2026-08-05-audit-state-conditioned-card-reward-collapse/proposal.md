## Why

The consumed state-conditioned simulator experiment stopped at canary because
its trained policy selected `take` on all 1,458 card-reward decisions despite
1,437 skip opportunities. The terminal bundle proves the failure but does not
show when the policy became saturated or which recorded training dynamics are
consistent with it, so another algorithm or experiment would currently be
guesswork.

## What Changes

- Add a deterministic, standard-library audit of the already published
  terminal rows, checkpoints, and canary diagnostics.
- Trace per-chunk card-reward action opportunities, stochastic selections,
  softmax probability mass, score margins, entropy, outcome summaries, and
  post-update parameter movement, with non-card categories as descriptive
  controls.
- Publish machine-readable and Markdown reports that identify the first
  observed warning and saturation boundaries, separate observations from
  hypotheses, and record all source identities and material evidence gaps.
- Add synthetic regressions for schema rejection, numerical summaries,
  boundary classification, deterministic publication, and prohibited holdout
  access.
- Keep the audit strictly read-only: no seed replay, native loading, training,
  fitting, model selection, threshold changes, gameplay, CommunicationMod, or
  successor authorization.

Success means the frozen terminal bundle produces byte-stable, independently
checkable evidence that narrows the collapse to explicit chunk boundaries and
states what the retained artifacts cannot establish. Failure leaves the
existing terminal result and `no_go` decision unchanged; rollback is removal
of the additive audit code, tests, reports, and planning artifacts.

## Capabilities

### New Capabilities

- `noncombat-state-conditioned-collapse-audit`: Deterministic read-only
  diagnosis of action-family collapse from a consumed state-conditioned
  simulator experiment's retained artifacts.

### Modified Capabilities

None.

## Impact

The change adds one analysis-only module, focused tests, a frozen audit report,
and project-direction documentation. It reads the tracked terminal experiment
bundle under `reports/` but does not modify that bundle or any gameplay,
simulator, training, checkpoint-loading, or production-policy surface. It adds
no runtime dependency beyond the Python standard library.
