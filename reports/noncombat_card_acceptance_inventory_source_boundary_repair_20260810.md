# Card-Acceptance Inventory Source-Boundary Repair

## Decision

The source-boundary repair is technically ready for closeout. The consumed
`20260810-r1` inventory identity remains terminal and must not be retried,
resumed, repaired in place, or reinterpreted as a completed inventory. This
report grants no inventory, native, model, environment, training, evaluation,
gameplay, qualification, promotion, or registration authority.

A distinct future inventory identity may proceed only as a separate OpenSpec
proposal with fresh source, request, review, approval, authorization, launch,
and no-retry bindings. That future proposal is a planning GO; execution remains
NO-GO until its own gates are reviewed and satisfied.

## Consumed Failure Binding

- Parent source HEAD and `origin/master`: `92b0fc6c1318bce5c99796bb21f830620e616e5f`.
- Request SHA-256: `d6016a7e8d47c7131cf903c97f0fd80f7ea8c013c653fb625cf983bc73c7d628`.
- Authorization SHA-256: `5155584920d6d58c4cea6bcefb784d528c22f657008a7c1f48b46ab067d9495b`.
- Launch observation SHA-256: `3f006cbf5921f71e97411db0bb4c61e755d97f572e610f2ce4bb09ff60312996`.
- Failure SHA-256: `4b59914dfe94d5511f2172608d101e7ad7bbbb52b01a7a6fab1c7b305115fa92`.
- Failure review SHA-256: `d50678313ac4be90afc3197da1623a0a4789c7e41337e261f8bae95219b91a0e`.
- Failure file SHA-256: `3b8abbdc73f193afdca71e09aa1a7de89d920c906421ef0cba980abaa7ef3898`.
- Failure review file SHA-256: `2a0246ffcec639efc13b9f531f73cf6119fea5e837bf769402111e33216b5b19`.
- Launch file SHA-256: `97b21e19484686325f6431e2731bd1d610062dbe7a465fdc5238f52733580f38`.
- Offending Git blob: `7127a5234ab1a9656895532a26269ee30f8df82e`.
- Offending payload SHA-256: `6e7a0ab7da295e310b0da01757ab33883c61c6e11aa30d43fc1e529e4988bdc3`.

The sole r1 invocation failed while parsing the tracked readiness staging path
before cohort selection, output staging, publication, native loading,
environment construction, model loading, training, evaluation, or gameplay.
The registered output and staging roots were absent after failure.

## Repair Boundary

The scanner now classifies generated direct children of `reports/` before
format handling and Git blob batching. Hidden direct roots with exact
`.scratch`, `.sealed`, `.staging`, `.temporary`, or `.tmp` suffixes and direct
roots ending `_attempts` are excluded with fixed kinds. Existing candidate
output and card-acceptance-specific rules remain in force.

The rule does not exclude non-hidden direct roots ending `.staging`, hidden
roots that merely contain a generated token, nested token-named directories,
ordinary filenames containing tokens, or direct names that merely contain
`attempt`. Malformed ordinary evidence still fails strict parsing.

## Verification

- Valid RED: the exact readiness path and generic generated roots reached
  ordinary parsing before the repair; the first generic malformed JSON failed.
- Independent review found that putting the exact long path in a synthetic Git
  worktree exceeded Windows path limits under the registered pytest temp root.
  The regression was split into an in-memory exact-path registry/blob boundary
  and a shorter same-shape Git integration case before final verification.
- Negative RED-boundary run: two ordinary-path protections passed while the
  generated-root case failed.
- Focused final pytest: `4 passed in 4.96s`.
- Complete seed-inventory pytest file: `17 passed in 23.80s`.
- Isolated compile probe: passed.
- Isolated import probe: passed with no Torch, native adapter, runtime,
  spirecomm, or gameplay import.
- `git diff --check`: passed.
- Strict OpenSpec validation: passed.
- Independent review initially raised the Windows path-length P1 described
  above; after the split regression and registered-temp reruns, re-review
  reported `No actionable findings`.
- The synchronized change was archived at
  `openspec/changes/archive/2026-08-09-repair-card-acceptance-inventory-source-boundary/`.
- Post-archive global strict OpenSpec validation: `82 passed, 0 failed`.

The first sandboxed pytest attempt and one host attempt were infrastructure
failures caused by Windows temp permissions and path length; neither was counted
as RED or GREEN evidence. Final evidence uses fresh children under the
registered system-temp parent.

Reviewed at `2026-08-09T22:56:10Z`.
