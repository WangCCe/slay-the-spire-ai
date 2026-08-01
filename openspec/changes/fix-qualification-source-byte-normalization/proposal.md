## Why

The consumed r7 qualification failed at `source_validation_failed` because the
reviewed source validator always rehashed worktree bytes with
`core.autocrlf=true`. Exact replay of review commit `ad4a74d9` proves that the
tracked `.gitignore` raw bytes match its reviewed blob `0c35857e...`, while the
forced normalization produces `0ed18f9e...` and falsely rejects the clean
source before `source_verified`.

## What Changes

- Add a regression with a reviewed CRLF blob that fails under the current
  normalization-only check, plus protection tests for normalized checkouts and
  substantive or binary tampering.
- Accept a reviewed source file when its raw Git blob hash matches the review
  tree exactly. Only when raw bytes differ may the validator try the existing
  controlled `core.autocrlf=true` normalization path.
- Keep `.gitattributes` raw-byte validation and admit only the existing safe
  text tokens plus Git's built-in `binary` token already present in reviewed R;
  arbitrary macros, filters, and external conversions remain forbidden.
- Keep no-follow reads, opened-file identity binding, index checks, untracked
  executable rejection, and fail-closed behavior unchanged.
- Record the r7 diagnosis and offline replay evidence without modifying or
  retrying r7, preparing r8, launching Slay the Spire, or changing any training
  authority.

Success means the raw-byte and built-in-attribute regressions fail before their
fixes and pass after them, the normalized-checkout and unsafe/tamper regressions
remain green, the exact reviewed source replay passes in a clean offline
checkout, focused and registered test gates pass, and strict OpenSpec
validation passes.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pre-request-qualification-observability`: define safe reviewed-source byte
  acceptance for exact Git blob bytes and permitted checkout line-ending
  normalization without weakening source-integrity checks.

## Impact

- Runtime source validator:
  `scripts/run_noncombat_outcome_evidence_expansion.py`.
- Regression coverage: `tests/test_noncombat_outcome_evidence_runner.py`.
- Evidence: a repository report that binds the immutable r7 failure and the
  clean-checkout hash replay; historical r7 artifacts remain unchanged.
- Non-goals: no request or bootstrap schema change, no timeout adjustment, no
  CommunicationMod configuration change, no game launch, no study start, no
  trajectory collection, no OPE, no training, and no policy promotion.
- Rollback: before any later replacement qualification is registered, this
  source change can be reverted normally. Any later attempted identity remains
  immutable evidence and cannot be repaired or retried by rollback.
