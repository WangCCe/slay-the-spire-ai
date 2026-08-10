## Why

R4 proved that the compact inventory build is bounded, but a commit-review tool
could still invoke `verify-inventory` with the earlier build authorization and
launch observation before the planned verification boundary existed. The
outer report artifacts were not enforced by the production CLI, so review
discipline alone could not prevent an unregistered source-rescanning operation.

## What Changes

- Require `verify-inventory` to consume a distinct canonical verification
  request, reviewed verification authorization, and fresh verification launch
  observation in addition to the immutable build request/authorization,
  approval, receipt, and inventory it verifies.
- Reject missing, predecessor, mismatched, unknown-field, noncanonical, or
  broadened verification authority before inventory, registered Git blob,
  seed, cohort, native, model, or environment access.
- Add an exclusive immutable verification execution receipt. Once its path is
  created, any complete, partial, empty, or invalid receipt blocks every later
  invocation of that verification identity.
- Bind the verification request to the exact build request, source commit,
  inventory/receipt identities, fixed v4/64 MiB/2,048-byte contracts, read-only
  reconstruction authority, and all-false downstream authority.
- Keep `build-inventory` compatibility unchanged and add RED/GREEN regressions
  for missing distinct authority, old build launch substitution, pre-access
  rejection, receipt interruption, duplicate invocation, and one exact
  source-only verification completion.
- Do not preregister r5, run another inventory verifier, publish a registration,
  train, evaluate, load native/model/runtime state, start gameplay, or grant
  downstream authority in this change.
- Live evidence is the reviewed r4 terminal boundary and postmortem through
  `11d39aea0`. Success is production-enforced rejection of the command shape
  that escaped r4, plus focused and full-gate proof; a proposal or report-only
  authorization is not success.
- Before a verification receipt exists, rollback removes only additive
  uncommitted hardening artifacts. After any receipt exists, preserve it and
  require a distinct successor identity rather than deleting, repairing, or
  retrying it.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-card-acceptance-empirical-successor`: Make distinct verification
  request/authorization/launch evidence and an immutable one-shot verification
  receipt mandatory production inputs before source-only reconstruction.

## Impact

The change affects
`analysis_scripts/noncombat_card_acceptance_empirical_successor_seed_inventory.py`,
its owning tests, the standalone successor verifier only if receipt binding is
needed there, and the existing empirical-successor specification. It changes
no gameplay policy, simulator semantics, seed selection, cohort sizes, compact
inventory schema, dependency, CommunicationMod configuration, model, or
checkpoint.
