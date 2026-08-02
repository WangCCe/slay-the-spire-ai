# R8 Request-Source Launch Diagnosis

## Scope And Disposition

This is a read-only diagnosis of the retired r8 no-action qualification. It does
not authorize or perform an r8 retry, an r9 preparation, a game launch, a study
start, trajectory collection, OPE, policy changes, reward changes, or training.
The immutable r8 root and all historical preparation/publication artifacts remain
unchanged.

## Frozen Evidence

- Reviewed request source:
  `reports/noncombat_outcome_evidence_expansion_20260716_v2_r8_qualification_request.json`
  - file SHA-256: `465c07ea7f2bb28c29dcce77e8f3e55f879e0ad0668f2c727f33b277aa026f72`
  - size: `10594`
  - request hash: `97fe82629d18981067720fce393fe6b0bb7095b78d7a6541cd4f45f754eb7e2d`
  - source S: `519cf55fa17706e7faee05a05c3a9c85f4238b75`
  - review R: `1d805b450862d2b5f34aeb2d4bbbeb9884510c84`
- External publication record:
  `D:\PycharmProjects\slay-the-spire-ai-r8-qualification-evidence-20260802\r8-publication-record.json`
  - file SHA-256: `a5db591cc13919435c5e32fb2c069f47f09af85e434cec18dbe814f0c18c3658`
  - recorded final command-vector SHA-256:
    `4538f17b923c338cea8255212951e3f3e648c82375aeeb19b409c557bca26135`
- Immutable bootstrap root:
  `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r8`
  - final successful stage: `source_verified`
  - stage-3 record hash:
    `54e2867b74e2b96f3cbc2bf8611f19b2fb7edea264e414d0f76d37005d883ba6`
  - terminal bootstrap code: `request_validation_failed`
  - failure record hash:
    `6333769e0df0132cd2835b8d53a4aefb22ad1ccfbe89fc942d7f54aa3797b22d`

## Root Cause

The reviewed request records two deliberately different paths:

- `request_source_path` is the committed, reviewed file:
  `D:\PycharmProjects\slay-the-spire-ai\reports\noncombat_outcome_evidence_expansion_20260716_v2_r8_qualification_request.json`.
- `request_path` is the active publication target:
  `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r8\qualification-request.json`.

The active path must remain absent until the parent has loaded and reviewed the
source request, validated prelaunch isolation, and exclusively publishes those
exact reviewed bytes. However, the frozen r8 checklist and the exact published
CommunicationMod command bind `qualify --request` to `request_path`, not
`request_source_path`. The runner therefore attempts its first request-source
read against a path that the protocol requires to be absent at that stage.

This is an offline launch-vector construction defect, not a request-byte,
bootstrap-prefix, runner-byte, or review-chain defect.

## Reproduction And Exclusions

Read-only reconstruction from the immutable claim and stage-3 records produced
the exact envelope SHA-256
`79c9fccf8b1c89cb60821a0fff677062d42508a9111ba28d872a5b66e80cedf8` and
passed `_qualification_bootstrap_validate_prefix_for_request` at
`source_verified`.

The pre-fix runner blob read from review R was byte-identical to the request
anchor
`97ed59092b41b32b9886b58f5c0906d77d23df9d7f59bf26f1d1c8f10efafe07`.
At diagnosis time, before this change edited the working tree, all fourteen
implementation paths matched their reviewed r8 hashes. The AI marker remained
at the request-bound count `15325`.

Replaying `load_qualification_request_source` with the committed source path,
review R, and the terminal failure entry treated as not yet published passes and
reconstructs review-binding hash
`7fc9c12ac809b6360eb2328ed831398d2ad0c8acc69188d1d1768b088f5495f3`.
The same loader cannot begin from the published active-path argument because
that file is correctly absent. This matches the observed ordering: launcher,
runner, and source validation pass; request validation fails before
`request_reviewed` or active-request publication.

## Required Fix And Gate

Future qualification preparation must build the ordered qualifier suffix from
the reviewed request and bind `--request` to `request_source_path`. The exact
final CommunicationMod-equivalent vector must be compared with that canonical
builder before publication. A vector that uses `request_path` must fail offline.

The source fix is complete only after an r8-shaped regression, focused Windows
pytest, strict OpenSpec validation, the registered commit gate, and independent
review pass. No live validation belongs to this change; any replacement identity
requires a separate amendment and fresh authority.

## Verification

- The focused qualification slice passed: `14 passed, 384 deselected`.
- The final serialization-bound regression set passed after review:
  `3 passed, 395 deselected`.
- Strict OpenSpec validation passed all 44 changes/specifications.
- The registered `commit` gate passed outside the restricted Codex sandbox:
  `3134 passed in 161.53s`. An earlier sandboxed invocation is not counted; its
  pytest basetemp ACL produced Windows access-denied setup errors rather than
  assertion failures.
- Independent review found no remaining code-level defect after the final
  properties round-trip validation and documentation corrections.
- The r8 request, publication record, six-file immutable root, and restored
  CommunicationMod configuration retain their frozen SHA-256 and byte sizes.
  The registered study root remains absent and no Java, game, Python,
  live/external qualification, study, or training process is running.
