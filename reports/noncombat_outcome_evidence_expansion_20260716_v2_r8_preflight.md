# R8 Qualification Preflight

Date: 2026-08-02

Status: `OFFLINE_BOUNDARY_CONFIRMED`

## Historical Boundary

R7 remains an immutable consumed partial. A fresh isolated standalone-verifier
replay of its exact request and review anchors returned:

- `passed=true`
- `qualification_status=pre_request_partial`
- `partial_stage=source_validation_failed`
- `consumed=true`
- `launch_qualified=false`
- `retry_allowed=false`
- `study_start_authorized=false`
- `collection_authorized=false`
- `training_authorized=false`
- audit hash
  `bd027e83904adac7fc91cccc23497a85d075a8068c3b1f1a8c1d3e2548e6bb9c`
- bootstrap inventory hash
  `0642f8ba9e0a1c77c2023473ea8e658c90217addd1987c95ddd663f659c83e4a`

The tracked r7 closeout is 7,624 bytes with SHA-256
`65d12ca83f897775969c7b7d05cadd9688705f50857605cc692a7eeada363298`.
It is not edited or reinterpreted by this amendment.

## Source-Fix Boundary

The source diagnosis is 5,414 bytes with SHA-256
`f7a07330f400fb930b34e51134121aa6d75bcd3102df8c031f2f76f5efd8622c`.
The implementation and archive commits form a direct pair:

- fix: `76e84c678f77276f5f278ceb42836abf513d4eaa`
- archive: `f7a00fe1d1d76719f01e4c2ad6edb15ebe08e5b5`

The current qualifier runner is 364,051 bytes with SHA-256
`97ed59092b41b32b9886b58f5c0906d77d23df9d7f59bf26f1d1c8f10efafe07`.
The standalone verifier is 320,131 bytes with SHA-256
`44095dba9fab2fedda8752eca798038594ef89d2f9bd0ee9153b5b73670483f8`.

## Registration And Absence

The unchanged v2 registration is 19,796 bytes with file SHA-256
`a0e282699ede7d1ea38b2d81f029ce5e823b924d81c5ca7cdbc9a45ddc2eb6c2`
and canonical registration hash
`7df8036e111fb55ece15154796d494ea857a74984c9d1a224c2b61f8fc710ace`.

A lexical component-by-component no-follow audit found all 26 proposed r8 and
study targets absent with no reparse component. The checked surfaces were:

- registered study root, `run-lock.json`, and `study-ledger.jsonl`
- r8 root and `qualification-config.json`, `qualification-request.json`,
  `qualification-manifest.json`, `qualification-trace.jsonl`,
  `qualification-completion.json`, and `qualification-failure.json`
- r8 attempt, ready, and release handshake paths
- r8 bootstrap claim, failure, handoff, and all five ordered stage paths
- external r8 evidence root
- repository-local r8 checklist, config, request, and review candidates

The r8 root is fixed as:

`D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r8`

The external evidence root is fixed as:

`D:\PycharmProjects\slay-the-spire-ai-r8-qualification-evidence-20260802`

A fresh lexical no-follow audit also found that external root and all ten
fixed descendant evidence paths absent. The descendants are:

- `r8-precommit-codex-review.txt`
- `r8-focused-pytest.txt`
- `r8-postcommit-source-only-review.json`
- `r8-postcommit-codex-review.txt`
- `r8-offline-go-no-go.json`
- `r8-publication-record.json`
- `r8-live-observation.json`
- `r8-standalone-verifier.json`
- `r8-independent-attestation.json`
- `r8-closeout.json`

These names are frozen before R. The external root must remain absent until R
and its postcommit review have passed; later evidence may only be published to
the corresponding fixed path.

## Source Snapshot And Workspace Hygiene

The approved amendment was committed as source snapshot S:

`519cf55fa17706e7faee05a05c3a9c85f4238b75`

Before freezing S, source inventory failed closed on historical pytest
basetemp ACLs and ignored executable artifacts. The artifacts were preserved,
not deleted, at:

`D:\PycharmProjects\slay-the-spire-ai-test-artifacts-archive-20260802`

The reversible archive contains 153 top-level pytest directories, 14
`__pycache__` directories, untracked Superpowers residue, and the local
`.codex/config.toml`. The two tracked Superpowers Markdown reports were
identified and restored exactly. The resulting repository has no tracked
change and no untracked non-inert file; the qualifier's own source inventory
returns exact S.

R8 config, request, and checklist candidates were rendered twice in separate
processes from S and the same live baseline. Both renders produced:

- isolation baseline hash
  `990f7c1a26229b90e3e459effe700dcb3c1fcb4c0b407b59ab4999f168499d64`
- config SHA-256
  `5e09b11c1f74c89a269b712f7785d1abb4a4cc3df33b388b34c56ed2fc364485`
- request self-hash
  `97fe82629d18981067720fce393fe6b0bb7095b78d7a6541cd4f45f754eb7e2d`
- request file SHA-256
  `465c07ea7f2bb28c29dcce77e8f3e55f879e0ad0668f2c727f33b277aa026f72`

An exact Git comparison from source-fix commit `76e84c678` to S found no
change in any registered implementation path, focused qualification test,
test-gate runner, or gate manifest. The recorded `3134 passed` registered
commit gate and focused source-validation evidence are therefore reusable by
exact input identity; candidate-specific checks still run under this change.

## Live Baseline And Authority

An elevated read-only process query found zero `SlayTheSpire.exe`, `java.exe`,
`javaw.exe`, `python.exe`, or `pythonw.exe` processes. No launch was issued.

The current ordinary-game CommunicationMod file was read only. It is 534 bytes
with SHA-256
`7ec79e01f9293a19ead3c59a26b18bb75ef900afa3dbe45d657769fe46061862`
and points to the normal five-game conservative eval command. It was not
changed during preflight.

This preflight grants authority only to commit and implement the reviewed r8
offline amendment. It does not authorize publication, invocation, study
`start`, gameplay actions, trajectory collection, outcome inspection, OPE,
reward or policy changes, training, promotion, r7 retry, or r9 preparation.
Any runtime implementation finding stops r8 and routes through a separate
regression-backed OpenSpec change.
