## Context

The seed-inventory module is both importable as
`analysis_scripts.noncombat_card_acceptance_empirical_successor_seed_inventory`
and executable as a file. Its control module is intentionally imported lazily
during authority validation. Under `python -I <script-path>`, Python excludes
unsafe script-directory and working-directory entries from `sys.path`; the
lazy package import therefore fails before authority validation. Existing
isolated tests manually add the repository root and did not exercise the
registered CLI entrypoint.

r2 is terminal and cannot be reused. This change repairs and proves only the
entrypoint; a later r3 change must bind the resulting pushed source commit and
publish a distinct authority chain.

## Goals / Non-Goals

**Goals:**

- Make direct `python -I <script-path> check-dispatch` load the exact configured
  control module from the repository.
- Produce deterministic canonical evidence that isolated mode and the expected
  control contract are available.
- Prove the dispatch path reads no request or repository evidence and creates
  no receipt, staging, output, cohort, or registration artifact.
- Preserve package-import behavior and the existing source-only dependency
  boundary.

**Non-Goals:**

- Creating or authorizing r3.
- Building, verifying, or registering an inventory.
- Reading seed evidence or changing source classification/cohort selection.
- Loading native/model/runtime/game dependencies or performing training,
  evaluation, gameplay, qualification, or promotion.

## Decisions

### Bootstrap only direct script execution from the fixed file location

When `__name__ == "__main__"` and `__package__` is empty, the module inserts
`Path(__file__).resolve().parents[1]` at the front of `sys.path` before CLI
dispatch. It does not consult the working directory, `PYTHONPATH`, user site,
or an authority artifact. Package imports remain unchanged.

This preserves `-I` isolation from environment and user-site injection while
making the repository package reachable from its own fixed script path.
Changing the registered command to a `-c` bootstrap was rejected because it
would duplicate implementation in an authority artifact. Installing the repo
as a package was rejected as unnecessary environment state.

### Add a distinct side-effect-free check command

`check-dispatch` takes no paths or authority arguments. It imports the fixed
control module, requires its resolved file to be the expected sibling module,
calls the source-only `experiment_contract()`, and emits canonical JSON binding
the schema, normalized interpreter, working directory, script path and digest,
validated command tuple, isolated flag, module name/path, and canonical
contract digest. The process tuple is reconstructed only after `sys.orig_argv`
matches the exact four registered dispatch arguments.

Reusing `build-inventory` as a probe was rejected because any sufficiently late
failure could consume a one-shot receipt or inspect empirical source state.
Using `--help` was rejected because it does not import the control module that
failed in r2.

### Test the exact subprocess shape and the internal no-side-effect boundary

One regression invokes `sys.executable -I <absolute-script> check-dispatch`
from the repository root twice and requires byte-identical canonical output
with the complete process identity. A focused unit regression calls the real
`main(["check-dispatch"])` branch, replaces the control import, and makes all
authority/Git/seed/receipt/output lifecycle operations fail if called, proving
the command exits before those surfaces.

The production Windows interpreter is used for the actual test gate. The test
uses `sys.executable` so it remains runnable in other development environments
without changing the registered production command.

## Risks / Trade-offs

- [Risk] Adding the repository root to `sys.path` weakens isolation. ->
  Mitigation: derive exactly one path from the immutable script location, only
  for direct execution, while `-I` continues to exclude environment, current
  directory, and user-site paths.
- [Risk] A successful probe is mistaken for inventory authority. -> Mitigation:
  the command accepts no authority/output arguments, creates no lifecycle
  artifact, and the spec explicitly denies successor execution authority.
- [Risk] The control module later moves. -> Mitigation: require the resolved
  module file to match the fixed sibling path and fail closed on drift.

## Migration Plan

1. Add the failing exact isolated-subprocess regression and focused side-effect
   guard.
2. Implement the direct-script bootstrap and `check-dispatch` command.
3. Run focused and complete seed-inventory tests, import isolation, strict
   OpenSpec validation, diff checks, and independent review.
4. Commit and push the repair as a standalone source boundary, then archive the
   change. Only a later proposal may use that commit for r3.

Rollback removes the bootstrap, command, and tests before any r3 authority is
published. r1/r2 terminal evidence is never changed or deleted.

## Open Questions

None.
