## 1. Action-Relative Model

- [x] 1.1 Add regressions and validation for expanding every supported non-guard branch into an exact action-relative example.
- [x] 1.2 Implement the frozen state-action scorer, constrained abstaining selection, parent-freeze checks, and exact development-artifact roundtrip.

## 2. Fixed Training

- [x] 2.1 Add a source-bound fixed-fit runner with held-out value, ranking, calibration, selection, support, latency, and offline-integrity reporting.
- [x] 2.2 Commit and push one immutable training registration, execute the fixed CPU fit exactly once, and publish the bounded artifact and report without tuning or retry.

## 3. Fresh Policy Decision

- [x] 3.1 Add and test a source-bound matched LightSTS evaluator for guarded control versus the constrained action-relative scorer.
- [x] 3.2 If every offline integrity condition passes, commit and push one immutable fresh evaluation registration and run it exactly once on the registered seed-disjoint cohort. All fixed conditions passed; the recipe is retained only for a separately registered real-game validation.
- [x] 3.3 Apply the fixed decision, run focused and adjacent tests, validate and sync OpenSpec, archive the change, and commit only scoped code and bounded reports.
