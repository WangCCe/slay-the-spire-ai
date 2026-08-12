# R6 Training Postmortem

## Outcome

The single registered r6 training identity terminated before native loading,
environment construction, seed access, or an optimizer step. The preserved
terminal verdict is `training_process_failure_terminalized`; rollback restored
the registered control target, kept the candidate disabled, and verified
production isolation.

The launch reported `registered source public_dependencies[0] size is invalid`.
The registered dependency declaration includes `analysis_scripts/__init__.py`,
which is a legitimate tracked zero-byte package marker. The generic artifact
validator rejects every `size_bytes <= 0`, so source validation stopped before
training could begin.

## Verified Boundary

- Independent terminal verifier: `verified=true`
- Checkpoints: `0`
- Environment accesses: `0`
- Optimizer and shadow optimizer steps: `0`
- Charged training time: `0.0` seconds
- Rollback: `rollback_verified`
- Downstream training, canary, holdout, qualification, promotion, gameplay, and
  production-model authority: all false
- Terminal closure SHA-256:
  `5ae1a900ef9e47594c2b017d80d9e0b0ac69c75c047d8743c8368b1461bdf810`
- Recovery binding SHA-256:
  `b4970bf769deb01db7d797b0c7465cb25af91531f084d19f4f7fd7228f82dc13`

The verifier recovery path was covered by 8 focused tests and the complete
68-test training-runner verifier file. No full repository test suite was run
for this closeout.

## Decision

R6 is closed and must not be retried. It produced no candidate checkpoint, so
seal, canary, and holdout execution are ineligible and not applicable.

The next experiment is exploratory rather than qualification-grade: permit
tracked zero-byte source bindings, cover the boundary with focused regressions,
then create a new run identity for a short smoke training. Strict frozen-cohort
and no-retry gates return only after a model candidate exists for qualification.
