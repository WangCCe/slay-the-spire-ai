## 1. RED Artifact Boundaries

- [x] 1.1 Add table-driven producer and standalone-verifier regressions proving both exact readiness-derived namespaces are excluded before blob loading while legitimate and lookalike report paths retain existing handling.
- [x] 1.2 Add a bounded recursive-inventory regression proving a tracked prior readiness candidate cannot contribute historical rows or inflate the next candidate source bindings.
- [x] 1.3 Add readiness-runner regressions for canonical-ceiling and verifier failures that require owned staging absence before terminal receipt publication.
- [x] 1.4 Add negative cleanup regressions proving pre-existing or unowned staging is preserved and cleanup failure terminalizes once as `no_go_artifact_binding` without claiming independent verification.

## 2. Source-Only Repair

- [x] 2.1 Implement the exact producer-side readiness-derived path classifier before format selection and Git blob loading without changing inventory schemas or other report handling.
- [x] 2.2 Implement the independent verifier-side classifier and require producer/verifier included source-binding parity.
- [x] 2.3 Implement exact staging ownership tracking and bounded pre-terminal cleanup while preserving successful sealing, installed-output recovery, durable terminal, and no-retry semantics.

## 3. Verification And Closeout

- [x] 3.1 Run the focused seed-inventory and readiness suites with isolated Windows pytest temp paths and confirm no native, runtime, model, game, CommunicationMod, empirical, training, evaluation, or OPE operation occurs. (`119 passed, 1 skipped`; source-only test modules and all-false authority/operation checks only.)
- [x] 3.2 Strictly validate OpenSpec and obtain independent source review of exclusion scope, producer/verifier parity, cleanup ownership, cleanup-failure behavior, and unchanged ceilings. (`openspec validate --all --strict`: 77 passed; final independent review: no actionable findings.)
- [x] 3.3 Run the repository commit gate once, record its terminal result without retrying an infrastructure-only timeout, and do not launch readiness r4 or gameplay. (The sole invocation reached the 900-second outer limit and returned exit 124 after 904.4 seconds. Its exact runner/pytest processes remained alive, were terminated by PID, and were confirmed absent. No retry occurred.)
- [x] 3.4 Sync and archive the completed change, publish the source-only repair boundary in project direction, then commit and push one cohesive repair.
