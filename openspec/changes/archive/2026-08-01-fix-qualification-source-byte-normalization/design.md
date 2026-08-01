## Context

R7 consumed its one live identity after the bootstrap published `claim`,
`launcher_verified`, and `runner_entered`, then emitted
`source_validation_failed`. The frozen failure intentionally contains only a
bounded generic detail, so the historical root did not identify the rejected
path.

An offline clone at exact review commit `ad4a74d9` reproduces the failure with
no untracked files or source drift. `.gitignore` is stored as reviewed blob
`0c35857e...`; hashing its exact 2,122 worktree bytes without conversion gives
the same object ID, while the validator's unconditional
`core.autocrlf=true` conversion gives `0ed18f9e...`. The validator therefore
rejects reviewed raw bytes merely because the committed blob contains CRLF.

After raw-first acceptance, the same clean-R replay advances to
`tests/fixtures/qualification_history/.gitattributes` and rejects its reviewed
`**/root/** binary` line. `binary` is Git's built-in non-text macro and cannot
name an external filter or custom macro; the current allowlist omitted it even
though reviewed R has contained the exact directive throughout qualification.

## Goals / Non-Goals

**Goals:**

- Accept exact reviewed Git blob bytes before applying optional checkout
  normalization.
- Continue accepting a safe CRLF worktree representation of a reviewed LF text
  blob.
- Continue rejecting substantive text changes, binary changes, unsafe
  attributes, source replacement, and path or inventory violations.
- Accept the exact built-in `binary` attribute token used by reviewed fixture
  evidence while rejecting arbitrary macros and filters.
- Prove the fix offline against a deterministic fixture and the frozen review
  commit.

**Non-Goals:**

- Do not change bootstrap/request schemas, failure records, timeouts, or live
  orchestration.
- Do not modify or retry r7, prepare r8, or authorize study start, collection,
  OPE, training, policy changes, or promotion.
- Do not clean unrelated repository test artifacts as part of this source fix.

## Decisions

### 1. Accept the exact raw blob before normalized fallback

For every reviewed path that requires byte binding, compute the ordinary Git
blob object ID directly from the descriptor-read bytes. If it equals the tree
object ID, accept those exact bytes. If it does not, retain the existing
fixed-environment `git hash-object --path` check with
`core.autocrlf=true`; accept only if that controlled conversion reproduces the
reviewed tree object.

This orders the two valid representations correctly: an exact reviewed blob
cannot be invalidated by an unnecessary conversion, while a platform checkout
that differs only by permitted line endings remains usable. Treating
`.gitignore` as inert was rejected because raw-first comparison is stricter,
general, and preserves byte binding for every reviewed path.

### 2. Preserve strict `.gitattributes` handling with one built-in token

`.gitattributes` remains raw-byte exact and its directives remain limited to
the existing safe text tokens plus the literal built-in `binary` token. It
controls how the normalized fallback behaves and therefore must not use that
fallback itself. Custom `[attr]` definitions, `filter=`, `diff=`, `merge=`, and
all other tokens remain rejected.

### 3. Keep the live protocol unchanged

The immutable r7 failure remains generic and consumed. This change adds no new
failure field or live diagnostic path. Root-cause evidence is recorded in a
repository report, and release proof uses the same internal source validator
offline against an exact clean checkout before any later qualification is
proposed.

## Risks / Trade-offs

- [A malicious change normalizes to reviewed text] -> Only line-ending
  conversion performed by Git under the fixed safe attribute/config boundary
  is accepted; existing attribute inspection and substantive tamper tests stay
  mandatory.
- [A broad attribute allowance enables an external converter] -> Permit only
  the exact built-in `binary` token and retain a tracked unsafe-filter
  regression; do not permit custom macros or token prefixes.
- [Raw SHA-1 construction diverges from the repository object format] -> The
  qualification contract already requires 40-character Git object IDs and
  SHA-1 repositories; construct the standard `blob <size>\0<bytes>` object ID
  already used for `.gitattributes`.
- [Current dirty worktree replay fails for unrelated ACL artifacts] -> Use a
  clean exact-commit checkout for release replay and keep current-worktree ACL
  cleanup outside this change.

## Migration Plan

1. Add and run the exact-CRLF-blob regression red.
2. Implement raw-first acceptance and rerun focused source-integrity tests.
3. Replay the exact r7 review commit in a clean offline checkout.
4. Run the repository commit gate and strict OpenSpec validation.
5. Commit the source fix and diagnosis. A later separate amendment may prepare
   one new qualification identity; r7 remains immutable and cannot be retried.

Rollback is an ordinary source revert only before a later qualification
identity is attempted. Evidence from any later attempt remains immutable.

## Open Questions

None.
