# R7 Source Validation Diagnosis

Date: 2026-08-02

Status: `ROOT_CAUSE_REPRODUCED_OFFLINE`

## Immutable R7 Boundary

The consumed r7 qualification root remains unchanged at:

`D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r7`

Its five-entry bootstrap boundary reached `claim`, `launcher_verified`, and
`runner_entered`, then emitted `source_validation_failed` before
`source_verified` or active-request publication.

- Source S: `b9e5384ed8d2d0c78fb24fa59f65c00da0a1e73a`
- Review commit R: `ad4a74d919f48c48626fcb770842aff66a77206f`
- Failure file SHA-256:
  `0d665b6076ce29deb44f3962cd1d5458b4312258172ce13f904542ae9f110e2b`
- Failure record hash:
  `ab64bef50d13390071c44825bcbb26d940cc3700c2d88b976a50baaa3f717973`
- Failure code: `source_validation_failed`
- Last completed stage: `runner_entered`

The registered study root, active request, handshake, gameplay evidence, run
lock, and ledger were absent. R7 remains retired and cannot be retried. This
diagnosis grants no authority to prepare r8, start the study, collect
trajectories, inspect outcomes, compute OPE, train, or promote a policy.

## Exact Offline Replay

A disposable local clone was checked out detached at exact R with
`core.autocrlf=false`. It had no tracked changes or untracked files. Calling
`_qualification_bootstrap_validate_source` with expected review commit R
failed deterministically with:

```text
_QualificationBootstrapError: qualification bootstrap reviewed source bytes changed: .gitignore
```

The relevant object evidence is:

| Check | Object ID |
|---|---|
| R tree blob for `.gitignore` | `0c35857e8d8d50585642224a6791f0e4be18e04e` |
| Raw worktree bytes | `0c35857e8d8d50585642224a6791f0e4be18e04e` |
| `core.autocrlf=false` path hash | `0c35857e8d8d50585642224a6791f0e4be18e04e` |
| Forced `core.autocrlf=true` path hash | `0ed18f9ea58258a4e3ed902b7f0f6e50fd2306cb` |

The reviewed file has 2,122 bytes, 120 CR bytes, and 146 LF bytes. Its raw
bytes exactly match the reviewed Git blob. The validator nevertheless always
applies `core.autocrlf=true` to non-`.gitattributes` reviewed paths and compares
only that converted object ID, so it rejects the exact reviewed mixed-line-
ending blob.

No source change after R is needed to reproduce the failure. The review
commit, tracked cleanliness, untracked inventory, and live startup timing are
therefore not the cause of this specific r7 failure.

## Second Pre-Existing Replay Blocker

After applying raw-first acceptance locally, the clean-R replay advances past
`.gitignore` and then fails on the reviewed file
`tests/fixtures/qualification_history/.gitattributes`, blob
`1ba867588e0e5165d975d37805444658a1e806b9`, whose complete content is:

```text
**/root/** binary
```

The validator permits safe text and line-ending tokens but omitted Git's
literal built-in `binary` token. This second blocker did not produce the
historical r7 record because tree-order validation stopped first at
`.gitignore`; it would nevertheless stop every clean replay immediately after
the raw-byte fix. The source change therefore also needs to accept only the
literal built-in `binary` token while retaining rejection of custom macros,
filters, external conversions, and unreviewed attributes.

## Fix Boundary

The source validator should:

1. Compute the ordinary Git blob ID from the descriptor-read raw bytes.
2. Accept and freeze those bytes immediately when the raw object ID equals the
   reviewed tree object.
3. Only when raw bytes differ, try the existing controlled
   `core.autocrlf=true` path conversion so an LF blob can still accept a CRLF
   checkout representation.
4. Keep `.gitattributes` raw-byte exact, admit only the literal built-in
   `binary` token in addition to the existing safe tokens, and retain every
   existing path, identity, index, untracked executable, tamper, and
   fail-closed guard.

The fix is complete only after a red/green regression, focused source-integrity
tests, exact clean-R replay, the registered commit gate, and strict OpenSpec
validation. A replacement qualification remains a separate later change.

## Focused Fix Evidence

- Exact reviewed CRLF blob: RED on normalization-only validation, then GREEN.
- Reviewed built-in `binary` attribute: RED on the old allowlist, then GREEN.
- Normalized checkout, binary tamper, substantive text tamper, tracked external
  filter, and untracked attributes: GREEN after the fix.
- Combined focused result: `7 passed in 8.70s`.
- Qualification-bootstrap slice: `9 passed, 388 deselected in 10.62s`.
- Source-integrity ordering and replacement slice:
  `9 passed, 388 deselected in 15.10s`.
- Python compile checks for the modified runner and test module: passed.
- Exact clean-R replay after both fixes: `validated_bindings=466`.
- Registered `commit` gate: `3134 passed in 204.82s` (gate duration
  `208.07s`).
- Strict OpenSpec validation: `44 passed, 0 failed`.
- `git diff --check`: passed.

No game, CommunicationMod configuration, study artifact, trajectory,
checkpoint, training state, reward, or policy was created or changed by these
offline checks.

The final implementation diff is limited to raw-first reviewed-blob matching,
the exact built-in `binary` attribute token, and their focused regressions. It
does not change request schemas, failure schemas, timeouts, launch behavior,
or any gameplay or policy path.
