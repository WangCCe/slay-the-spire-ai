## Why

The published event-semantics coverage audit analyzes raw C++ case spans and
therefore treats commented-out `os <<` statements as live display evidence.
The registered r1 inventory demonstrably adds `Big Fish` label `Offer` and old
`Cursed Tome` labels `0: Take` and `1: Stop` from comments, so its label matrix
must not be used to design the next adapter contract.

## What Changes

- Add regression fixtures proving line comments and block comments cannot
  contribute event cases, return masks, display labels, effect indices,
  condition signals, or phase signals, while comment markers inside C++ string
  and character literals remain source text.
- Analyze a layout-preserving comment-masked projection of each C++ case while
  retaining the exact raw source span and hash for provenance.
- Fail closed on malformed comment or literal structure instead of falling back
  to regex interpretation of ambiguous source.
- Preserve the r1 registration and artifacts unchanged. Publish a fresh,
  implementation-bound r2 registration and canonical artifact set, then record
  an exact r1-to-r2 delta proving the expected false labels were removed and
  event, alias, status, and authority counts did not drift unexpectedly.
- Keep resolver extension, native simulator execution, seed use, gameplay,
  model fitting, reward changes, formal RL, training, and promotion out of
  scope.

Success means r2 contains no evidence originating only from C++ comments,
accounts for the same complete Current alias surface, reconciles every metric,
and recomputes byte-for-byte. The rollback boundary is removal of the parser
fix and r2 evidence; the immutable r1 result remains available as the diagnosed
predecessor.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-event-semantics-coverage-audit`: Require comment-aware C++ source
  analysis and an immutable superseding-evidence contract when a published
  coverage result is corrected.

## Impact

- Updates `analysis_scripts/noncombat_event_semantics_coverage_audit.py` and
  its focused tests.
- Adds a source-bound r2 registration, canonical artifacts, closeout/delta
  report, and project-direction correction without modifying Current,
  `sts_lightspeed`, the event resolver, or any runtime policy.
