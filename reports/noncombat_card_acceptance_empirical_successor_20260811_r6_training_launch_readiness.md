# R6 Training Launch Readiness

## Verdict

- Training request publication: `GO`
- Training authorization publication: `NO-GO`
- Training execution: `NO-GO`

The exact bounded training request is reviewed and pushed at `e5465e34e`, but
the repository has no registered production command that can execute it. An
authorization would currently grant a request that cannot be launched through
one source-bound, independently reviewable lifecycle.

## Evidence

- `noncombat_card_acceptance_empirical_successor_experiment.py` exposes only
  `contract`, `render-request`, `validate-request`, `render-authorization`, and
  `validate-authorization` CLI commands.
- `noncombat_card_acceptance_empirical_successor_runtime.py` exposes
  `run_bounded_paired_training` as a callback-driven library function and has no
  parser, `main`, or execution command.
- The runtime requires a constructed environment factory, exact remaining seed
  schedule, before/after environment hooks, deadline, checkpoint integration,
  and terminal publication supplied by a caller.
- The control plane already provides validated execution contexts, exclusive
  leases, write-ahead access/resource accounting, complete-boundary checkpoint
  publication, continuation classification, and terminal/rollback APIs, but no
  runner composes them.
- No exact training command is registered in the active design, spec, tests, or
  tracked report artifacts.
- The current active task cannot return its own latest-human-message watermark
  while the response is running. The required fresh approval-time revocation
  observation therefore cannot be constructed without guessing message
  identity or timestamp.

## Source Boundary

The registered experiment control and runtime files remain byte-identical to
source commit `525c302df2d54cf06c756a9dc55fbae4ed9cb8b0`. Later changes to the
seed-inventory and independent-verifier modules are additive r6 registration
construction/validation support. A runner must bind its own pushed source and
exact command without rewriting the registered experiment source identity.

## Required Successor

Add one narrow training runner and source-only launch manifest that:

1. binds the r6 registration, pushed request/review, exact runner source,
   Windows interpreter, output root, resource ceilings, and closed preflight,
   training, and dead-owner terminalization command set;
2. validates the later stage authorization and fresh approval/launch
   observations before runtime or native import, then requires a reviewed pushed
   command-specific envelope using the standing-delegation resolver or exact
   external-human approval to bind authority to a request-subordinate manifest/
   command/rollback composite without broadening the request;
3. verifies the registered control/runtime and public dependency bytes while
   separately binding the additive registration verifier used at launch;
4. owns the execution context, lease, access/resource ledgers, exact 512-seed
   schedule, eight per-chunk durable checkpoints, independently reconstructed
   component hashes, predecessor-linked canonical state continuity, and one
   terminal classification;
5. preserves setup-only reopen and the single complete-boundary continuation,
   while rejecting partial-chunk retry, substitution, tuning, or raised bounds;
6. binds an exact candidate-disabled rollback authority, control target, and
   production-isolation identities without rewriting the r6 registration file;
7. can terminalize a proven dead owner's partial prefix through registered
   rollback and process failure without runtime restoration, seed access,
   environment construction, model loading, or replay, using a fresh envelope
   bound to the exact old owner, lease and existing prefix rather than the prior
   run envelope, with a sibling guard, final pre-reclaim verification, and
   idempotent same-envelope closure-only resume;
8. provides source-only dry-run/preflight tests that require the output root to
   be absent and load no native module, model, environment, seed, or checkpoint
   before any authorization is created.

Until that runner is implemented, reviewed, tested, committed, and pushed,
parent tasks 6.4 and 6.5 remain incomplete and no training authority exists.
