## Context

Commit `3bdd870d836b1f6a1dc3cb42dc0c2e0b57779eb4` publishes the canonical
r2 registration and cohort-reuse proof. Registration authority is all false,
its SHA-256 is `8e0576bbf86b2334ccce67ac809410a02dcbfa6419f075211bbe48d0164f8549`,
and neither authorization nor output exists. The user explicitly approved the
exact one-shot CPU execution, including the pre-start stop rule and post-start
no-retry rule.

## Goals / Non-Goals

**Goals:**

- Publish a canonical authorization binding the pushed registration, r2 logical
  identity, and output path before any native load.
- Produce a source-only isolation preflight that proves every registered
  identity and no-game/no-checkpoint-mutation boundary.
- Execute or resume exactly one r2 attempt within its cumulative wall and
  episode bounds.
- Publish and independently verify the reached terminal evidence, including a
  valid negative or fail-closed result.

**Non-Goals:**

- Changing source, module, simulator, cohort, seeds, algorithm, reward,
  threshold, resource limit, or output path.
- Launching Slay the Spire, contacting CommunicationMod, or loading production
  policy checkpoints.
- Retrying after the started journal, treating a pre-start failure as authority
  to repair in place, or promoting any result into live policy use.

## Decisions

### Publish authorization before preflight

The authorization will be built with the existing closed schema and bind
registration commit `3bdd870d836b1f6a1dc3cb42dc0c2e0b57779eb4`, path, digest, and size;
logical identity `noncombat-simulator-rl-20260804-r2`; and output
`reports/noncombat_simulator_rl_experiment_20260804_r2`. It must be committed
and pushed before the source-only preflight can accept it. Only
`experiment_execution` becomes true; every other authority remains false.

### Separate source-only isolation evidence from native execution

Before preflight, record the CommunicationMod config digest, relevant process
inventory, production checkpoint inventory, and absence of r2 output/lease.
Run the existing source-only runner preflight against Windows Python, current
working source, pushed controls, module bytes, and physical simulator source.
Record the same isolation snapshot afterward and publish a canonical report.
Any mismatch stops before native loading. Hashing checkpoint files is allowed;
deserializing or modifying them is not.

### Use the repaired native-first execution path once

The execution command uses Windows Python, the registered shop-support adapter,
the physical simulator checkout, and CLion MinGW DLL directory. Fresh startup
loads and validates native before pristine Torch initialization and creates
output only afterward. A pre-start failure leaves output absent and stops for
review. Once output and the started journal exist, interruption may resume only
the same logical attempt; terminal failure cannot retry.

### Treat every registered terminal verdict as evidence

The standalone standard-library verifier must accept the final directory. The
closeout records resource use, reached coordinates, untouched cohorts, support
rate, and learning-signal verdict without changing formal readiness or granting
live authority. No source test suite is rerun unless source changes.

## Risks / Trade-offs

- **Credential or publication failure** -> Stop before preflight until the exact
  authorization blob is visible on `origin/master`.
- **Isolation drift between snapshots** -> Fail closed and do not load native.
- **Native/Torch compatibility still fails pre-start** -> Leave output absent,
  report the exact error, and do not repeat automatically.
- **Long execution is interrupted** -> Resume only from canonical journal and
  checkpoint state under the same controls and remaining cumulative time.
- **Canary fails or no learning signal appears** -> Publish that valid terminal
  negative; do not tune or extend.
- **Holdout is conditionally untouched** -> Preserve it when the registered
  canary gate fails; this is required, not incomplete execution.

## Migration Plan

1. Generate, validate, commit, and push the one-shot authorization.
2. Capture pre/post isolation, run source-only preflight, publish its canonical
   report, then commit and push it.
3. Run the exact execute command once and wait through its terminal state.
4. Independently verify artifacts and immutable r1/r2 controls.
5. Update direction, sync/archive this change, commit, and push closeout.

There is no rollback after the started journal. Before start, rollback consists
only of stopping and preserving the pushed controls; no replacement conditions
are chosen inside this change.

## Open Questions

None. Any unexpected identity or isolation difference is a blocking result.
