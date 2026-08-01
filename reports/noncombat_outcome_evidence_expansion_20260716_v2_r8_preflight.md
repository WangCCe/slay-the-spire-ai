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

A lexical component-by-component no-follow audit found all 27 proposed r8 and
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
