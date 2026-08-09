## Why

The sole authorized `20260810-r1` card-acceptance inventory build failed during
historical-source parsing because a tracked readiness `.staging` root was not
classified as generated evidence. The 6.7 MiB gzip expanded to a truncated
512 MiB JSON payload, so the operation stopped before cohort selection or
publication and the r1 identity is terminal and non-retryable.

## What Changes

- Classify generic generated roots directly below `reports/` by path shape,
  including hidden staging, scratch, sealed, temporary, and attempt roots,
  before format detection or Git blob reads.
- Keep the current successor output-specific exclusions and add explicit
  negative boundaries so similarly named ordinary files and directories remain
  eligible.
- Preserve and independently verify the r1 terminal failure; do not retry,
  resume, replace, or reinterpret its request, authorization, launch observation,
  or partial in-memory scan.
- Produce a source-only repair report and a separate go/no-go decision for any
  future inventory identity. This change does not authorize another inventory
  build.

Success means the exact offending r3 staging path and representative generated
root variants are excluded before blob access, ordinary historical evidence is
still scanned, focused producer/verifier tests and strict OpenSpec validation
pass, and independent review finds no actionable source-boundary issue.

## Capabilities

### New Capabilities

- `noncombat-card-acceptance-inventory-source-boundary`: Defines generic
  generated-root exclusion, pre-blob classification, negative path boundaries,
  and terminal handling for the consumed r1 inventory attempt.

### Modified Capabilities

None.

## Impact

The repair is confined to the source-only card-acceptance seed-inventory module,
focused tests, bounded reports, and OpenSpec/project-direction records. It does
not load Torch, native modules, models, checkpoints, environments, gameplay, or
CommunicationMod and does not access simulator seeds. Rollback before commit
removes only additive repair files or reverts the uncommitted classifier diff;
the pushed r1 failure evidence remains immutable in all cases.
