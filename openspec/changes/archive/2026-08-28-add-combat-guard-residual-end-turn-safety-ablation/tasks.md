## 1. Action Safety Boundary

- [x] 1.1 Add regressions proving the EndTurn constraint is applied before residual selection, exact guard abstention is preserved, and unrestricted behavior remains unchanged.
- [x] 1.2 Implement a registered forbidden-residual-action mask with explicit safety skip and intervention telemetry.

## 2. Three-Arm Evaluation

- [x] 2.1 Add a source-bound runner for guarded control, unrestricted residual, and EndTurn-masked residual on one fresh matched cohort.
- [x] 2.2 Encode and test the fixed control-relative, mask-enforcement, and masked-versus-unrestricted policy conditions.
- [x] 2.3 Publish both paired contrasts, all arm outcomes, intervention and EndTurn counts, support exclusions, latency, traces, provenance, and authority.

## 3. Fixed Execution And Closure

- [x] 3.1 Commit and push one immutable registration, then run the fixed three-arm LightSTS evaluation exactly once without fitting or gameplay.
- [x] 3.2 Apply the all-condition decision without changing seeds, threshold, artifact, mask, or recipe and without starting a second ablation. The mask improved the failed residual directly but did not pass every guarded-control condition, so the artifact is closed.
- [x] 3.3 Run focused and adjacent offline tests, validate OpenSpec strictly, sync the modified specification, archive the change, and commit only scoped implementation and bounded reports.
