# R8 Outcome-Evidence Qualification Review

Date: 2026-08-02

Status: `PRECOMMIT_REVIEW_READY`

## Identity And Scope

- Qualification ID:
  `noncombat-outcome-evidence-expansion-20260716-v2-qualification-r8`
- Source snapshot S:
  `519cf55fa17706e7faee05a05c3a9c85f4238b75`
- External root:
  `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r8`
- Registered study root: absent
- R8 external root: absent
- Target processes: zero at preflight
- Runtime source edits in this amendment: none

R1 through r7 remain immutable historical evidence. R7 is consumed and
non-retryable. This candidate cannot prepare r9.

## Candidate Anchors

- Registration SHA-256:
  `a0e282699ede7d1ea38b2d81f029ce5e823b924d81c5ca7cdbc9a45ddc2eb6c2`
- Registration canonical hash:
  `7df8036e111fb55ece15154796d494ea857a74984c9d1a224c2b61f8fc710ace`
- Isolation baseline hash:
  `990f7c1a26229b90e3e459effe700dcb3c1fcb4c0b407b59ab4999f168499d64`
- Config SHA-256 / size:
  `5e09b11c1f74c89a269b712f7785d1abb4a4cc3df33b388b34c56ed2fc364485`
  / 949 bytes
- Request self-hash:
  `97fe82629d18981067720fce393fe6b0bb7095b78d7a6541cd4f45f754eb7e2d`
- Request file SHA-256 / size:
  `465c07ea7f2bb28c29dcce77e8f3e55f879e0ad0668f2c727f33b277aa026f72`
  / 10,594 bytes
- Checklist SHA-256 / size:
  `55b9b70f3fe81c41491325136d20dbdb6a138301d6368997467badbb85919440`
  / 45,472 bytes
- Preflight SHA-256:
  `f1b7d96782ebd036f7eaa843811b63bc40c2033b34da450ddcdb9abb43de2528`

The candidate was rendered twice in separate processes from exact S and the
same live baseline. Config and request bytes, request self-hash, isolation
baseline, implementation map, and checklist bindings reproduced exactly.

## Launcher And Evidence Contract

The checklist now freezes the complete trusted-launcher prefix in argument
order: Windows production Python, `-I`, `-S`, `-c`, the exact trusted launcher
code, the reviewed runner path, and the reviewed runner SHA-256. The launcher
code is 27,125 UTF-8 bytes with SHA-256
`1d2d0fc0b4c56f303cd5fe5e1778e878ff22be93288b112b0e435a826f396877`.
The runner remains 364,051 bytes with SHA-256
`97ed59092b41b32b9886b58f5c0906d77d23df9d7f59bf26f1d1c8f10efafe07`.

The ordered qualifier arguments are frozen as `--registration`, `--request`,
`--request-hash`, `--request-file-sha256`, `--request-size`, and
`--review-commit`. Only the bootstrap envelope and launch token remain
postcommit-derived; their named builders and complete input sets bind request
bytes, request size, S, R, runner bytes, and the qualification root.

The external evidence root and ten exact descendant paths are also frozen.
They cover precommit review, focused pytest, postcommit source-only review,
postcommit independent review, offline go/no-go, publication, live
observation, standalone verification, independent attestation, and closeout.
A fresh lexical no-follow audit found the root and every descendant absent;
the root must remain absent until R and its postcommit review pass.

## Verification

- Fresh r7 standalone replay: passed with historical audit hash
  `bd027e83904adac7fc91cccc23497a85d075a8068c3b1f1a8c1d3e2548e6bb9c`
  and `retry_allowed=false`.
- Qualifier source inventory at S: passed; post-hygiene untracked executable
  path count is zero.
- Candidate-specific producer/verifier focused pytest: `43 passed in 74.21s`.
- Runner and verifier memory compile: 2 passed.
- Strict OpenSpec validation: `44 passed, 0 failed`.
- `git diff --check`: passed.
- Registered commit gate: reused `3134 passed in 204.82s` only after an exact
  Git comparison proved every registered implementation path, focused test
  input, gate runner, and gate manifest unchanged from the source-fix release
  inputs.
- Source-fix focused evidence: exact reviewed bytes, normalized fallback,
  built-in `binary`, tamper, filter, source-order, and replacement checks all
  remain bound by identical test bytes.
- Raw unregistered full suite: not run.

Two sandboxed pytest attempts produced only Windows basetemp ACL setup errors
before assertions. Their repo-local basetemp was preserved outside the
repository and they are not counted as regression evidence. The same focused
selection passed under the already-required host execution boundary.

## Proposed Direct-Child Review Tree

R must be the direct child of S and may change exactly these inert paths:

1. `openspec/changes/qualify-r8-outcome-evidence-replacement/tasks.md`
2. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r8_preflight.md`
3. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r8_qualification_checklist.json`
4. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r8_qualification_config.json`
5. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r8_qualification_request.json`
6. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r8_qualification_review.md`

Every path has an inert suffix. No implementation, test, registration,
CommunicationMod, game, checkpoint, model, reward, or policy byte enters the
review tree. Before commit, the staged path set and canonical candidate bytes
must match this list exactly. After commit, source-only replay must prove
`parent(R) == S`, `HEAD == R`, exact implementation equality across S/R, and
the reviewed request bytes.

## Authority Boundary

The precommit decision remains `no-go`; publication and invocation are false
until postcommit source-only and independent review pass and an external
offline go/no-go record is published. Even a later `go` authorizes only one
no-action r8 qualification invocation. It does not authorize study `start`, a
run lock, gameplay action, trajectory collection, outcome inspection, OPE,
reward or policy changes, training, or promotion.
