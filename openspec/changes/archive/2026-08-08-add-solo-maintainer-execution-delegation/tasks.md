## 1. RED Delegation Contract

- [x] 1.1 Add producer RED tests for canonical standing-delegation v1 construction, exact closed scope/exclusions/provenance/revocation fields, self-digest, and rejection of missing, unknown, hybrid, malformed, stale-digest, or self-consistently scope-tampered fields.
- [x] 1.2 Add producer RED tests for delegated-approval v2 binding the complete delegation and exact request, authorization transitive binding, request/delegation/resolution drift, and generated text never appearing as v1 verbatim human approval.
- [x] 1.3 Add independent-verifier RED tests that accept valid delegated approval and reject the same mechanically detectable tamper matrix without importing producer, Torch, native, gameplay, or CommunicationMod modules.
- [x] 1.4 Add RED source-only CLI tests for delegation inspection, delegated-approval rendering, authorization rendering, canonical stdout, invalid-input failure, and zero empirical side effects.
- [x] 1.5 Add historical-preservation tests proving the real consumed v1 registration/approval/authorization/terminal bytes and existing v1 validation behavior remain unchanged.

## 2. Minimal Producer And Verifier Implementation

- [x] 2.1 Add closed schema constants plus public standing-delegation builder/validator functions to the standard-library control plane.
- [x] 2.2 Add delegated-approval v2 construction and exact schema dispatch while preserving historical external-human approval v1 and the unchanged authorization schema.
- [x] 2.3 Add source-only CLI commands to inspect delegation, render delegated approval, and render authorization from canonical files without publishing or executing them.
- [x] 2.4 Independently implement the same closed delegation, v2 approval, request, and authorization validation in the terminal verifier without importing producer helpers.
- [x] 2.5 Keep runtime, native adapter, experiment controls, output inventory, journal/resource/retry lifecycle, and terminal verdict semantics byte- or behavior-unchanged outside the required approval dispatch.

## 3. Source Verification And Publication

- [x] 3.1 Run focused producer, independent-verifier, CLI, preservation, import-isolation, and directly dependent source-preflight tests with a fresh system-temp pytest child.
- [x] 3.2 Run Python compilation/import probes, strict validation of this change and the complete OpenSpec tree, and `git diff --check`; confirm no empirical output, native/model load, environment, seed, fitting, training, evaluation, gameplay, CommunicationMod, qualification, promotion, or execution occurred.
- [x] 3.3 Obtain an independent code/spec/security review, add RED regressions for accepted findings, and make only narrow source fixes.
- [x] 3.4 Invoke the repository `commit` gate exactly once at the final source boundary, record correctness and duration, and do not rerun solely for the known feedback-duration problem.
- [x] 3.5 Update project direction to preserve r4 as historical-only for changed source and name a separate fresh readiness change as the next step.
- [x] 3.6 Sync the accepted delta spec, archive this change, commit, and push only scoped files while preserving historical evidence and unrelated artifacts.
