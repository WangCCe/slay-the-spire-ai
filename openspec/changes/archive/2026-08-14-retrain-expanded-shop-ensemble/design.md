## Context

The existing cross-validation runner already implements exact dataset loading, five source folds, five initialization seeds, epochs `8/16/32`, vote quorums `3/4/5`, Current-relative loss, no-go artifacts, frozen ensemble serialization, and a 32-source fresh gate. The only new training input is a verified 384-source canonical partition with SHA-256 `99efae73450c3848b04ea487a2e9ca9597430a78d1bebbea61b27bb00da0b3de`.

## Goals / Non-Goals

**Goals:**

- Reuse the unchanged cross-validation implementation on exactly 496 unique shop sources.
- Bind and report the expansion cohort separately while retaining source-level fold isolation.
- Freeze before any access to the reserved 32-source fresh schedule.

**Non-Goals:**

- Changing model architecture, objective, optimizer, epoch grid, quorum grid, or gate checks.
- Comparing additional baselines or tuning after OOF/fresh access.
- Live policy integration or gameplay.

## Decisions

### Add a thin source-binding wrapper

The new runner will construct a five-dataset binding tuple and delegate loading, OOF training, ensemble fitting, evaluation, and artifact writing to the existing tested runner. Editing the old default bindings was rejected because it would obscure the historical 112-source experiment boundary.

### Preserve the original selection gate

The 496-source run uses the same eligibility conditions that rejected all 112-source configurations. This isolates data scale as the intervention. If no configuration is eligible, preflight writes a terminal no-go and the fresh schedule remains untouched.

### Use the reserved fresh schedule only after source commit

If OOF succeeds, the wrapper and frozen dataset bindings are committed before native evaluation on `95492..95555`. The model, epoch, and quorum may not change after fresh access begins.

## Risks / Trade-offs

- [Training 75 models on 496 sources is slower] -> Keep the registered grid unchanged and allow a bounded two-hour OOF preflight.
- [Expanded data may still not transfer] -> Require both OOF and untouched fresh gates; failure is terminal.
- [Thin wrapper depends on private helper functions] -> Bind the exact underlying source files and add focused delegation/identity regressions.

## Migration Plan

Commit the wrapper, run one source-only OOF preflight, and stop on no-go. If eligible, run one native fresh evaluation, verify artifacts, and archive the change. Current remains unchanged in all cases.

## Open Questions

None.
