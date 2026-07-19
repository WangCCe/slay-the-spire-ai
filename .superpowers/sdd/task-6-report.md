# Task 6: Complete V3 Terminal And Historical Replay

## Scope

Task 6 adds verifier-only support for complete request-v3 terminal evidence. The
verifier reconstructs the bootstrap summary from one guarded snapshot and
requires exact matches in result-v3 and review-binding-v3 before audit-v3 can be
verified. No producer lifecycle, gameplay, live launch, policy, or training code
changed.

## TDD Evidence

The first literal terminal/history RED selected eight tests: `7 passed, 1
failed, 556 deselected`. The sole failure was the frozen Task 5 rejection:
`qualification terminal-v3 verification is not implemented`.

A second focused RED proved that an incomplete failed v3 lifecycle was wrongly
accepted: `1 failed, 314 deselected`. The schema-gated fix now requires a passed
v3 terminal with one child, exit code zero, complete attempt/ready/release,
restored isolation, and a dead child.

Final terminal/history GREEN:

```text
94 passed, 556 deselected in 19.89s
```

## Literal V3 Vector

The vector was rendered from the independent test fixture at the fixed report
root `.superpowers/sdd/task-6-vector-temp` and then removed.

| Field | Value |
| --- | --- |
| request hash | `4a64dbe193b981fda14043c0c98f3a5c2af3c11c1430a0df7909381029bc41ce` |
| request file SHA-256 / size | `e0e943bf9a63b7d6534a247fadd6af2933b3408ba92672895778cbe27f325198` / 6425 |
| result hash | `beae07fde11c2fe4bb8a2bdfa5fd0e0a74c44f505664ea3a8f9c2aadadc40fa2` |
| result file SHA-256 / size | `39ed870033f34c84917af47a0a3949c14641053387e611cb69e5b606052b64b3` / 8968 |
| review binding hash | `1099d574ee333e3233615b2203b097c11669ec2dfa9852d057e6da1ab35c06c7` |
| claim hash | `6fd39b36efd1eb701da3cd7c57453cab6443134ac9cfdb751bde39801af6aad8` |
| final stage hash | `28315f1f8bd175ea2fb098b8f0f56da85d7ef2a68aae7b11693febabece98c9c` |
| handoff hash | `735927f23212ba65c5e30451e8831ba9536b22e7359f2c54d61ac6c28d92cc82` |
| launch token | `120c25e4f59acae54db3e86128ae9225f4ea09285084cd1594b0a3774e9ddae2` |

The fixture builds request, claim, five stages, active request, handoff,
attempt, ready, release, isolation baseline/post-observation, result, and review
bytes literally. Producer request/record/result/review/inventory/token builders
are patched to fail if called. A separate `-I -S` subprocess loaded the verifier
by source with the producer absent from `sys.modules`; it passed with
`producer_absent=true`, complete isolation, and launch-qualified evidence.

## Historical R1-R6 Fixtures

Each reviewed Git blob is read with `git show` and pinned by exact size and
SHA-256. Explicit v1/v2 dispatch emits audit-v2, adds no bootstrap or retry
field, keeps launchability false, and keeps every authority false.

| Fixture | Blob SHA-256 / size | Schema | Record hash | Classification | Consumed |
| --- | --- | --- | --- | --- | --- |
| r1 | `8c1afc4a2968717540353e4a65810103dd56bb6a85b008a6ed8043bb48938bba` / 21249 | request-v1 | `ccd76824c90a9726c57b48a7f71d8bc1d8da94df6c686ae36eff10a1b72db41f` | `failed_pre_ready` | true |
| r2 | `8c1afc4a2968717540353e4a65810103dd56bb6a85b008a6ed8043bb48938bba` / 21249 | request-v1 | `8bb9b396e129e017fd84fb4aabe7fa6d02bb51b0c7c147836dbf29e7c289c95c` | `failed_readiness_timeout` | true |
| r3 | `739fbb650e2694844e48062c1c0892a6778e5de8965a3f39bf076f80a309b41f` / 12245 | request-v1 | `e495ce302f0ddf9628962e0d4147614a0cf9b9c7c010f256662a98eae76b033d` | `failed_release_side` | true |
| r4 | `739fbb650e2694844e48062c1c0892a6778e5de8965a3f39bf076f80a309b41f` / 12245 | request-v1 | `f21313b80fedfccdea76c0e69d3d3d44f06289ba033159537d73f0202f3c039e` | `obsolete_prepared` | false |
| r5 | `40e978059c31f90c2da52435d50193deea95b1f3f19c28a865ef96f80c20ed26` / 8813 | request-v2 | `b80b5311018c6c39de6df55c8e1d9090826e07bbd606711b4d0c4d68b4d1cfce` | `retired_pre_request` | true |
| r6 | `680f6cffba77d8134500f1ef9f6d4ca02e4df05916afc1926bab2262e8000d62` / 5952 | request-v2 | `fc5332ffca8b00a1e5132047d07538825369f187db030d9e080a91d37fa8496c` | `retired_pre_request` | true |

## Mutation Coverage

The rejection matrix covers every declared bootstrap path, every record byte,
every inventory row path/hash/size and ordering, schema, anchor, PID, stage link,
handoff active-request/hash/size links, result and review bootstrap fields,
review request/allowed-path/implementation/registration/source/review anchors,
external request/result hash/size/review commit, handshake links, exit/liveness,
restoration, timestamps, terminal branches, terminal self-hash, incomplete failed
lifecycle, and guarded alternate artifacts. Invalid v3 terminals are consumed,
non-retryable, sealed-invalid, launch-unqualified, and authority-free.

## Verification

```text
Task 5 focused review:             26 passed, 289 deselected
Task 5 prefix/classification:      71 passed, 244 deselected
History/import compatibility:       7 passed, 308 deselected
Terminal/lifecycle compatibility: 131 passed, 519 deselected
OpenSpec change strict:             valid
OpenSpec all strict:                41 passed, 0 failed
py_compile:                         passed
git diff --check:                   working-tree-only; superseded below
```

The earlier broad qualification and full verifier attempts timed out while
buffering and are not counted as passes. Per the Task 6 brief, no repository
full-suite completion is claimed.

## Self-Review And Boundary

The verifier imports no producer module or builder. Historical review-binding
v1, request/result v1/v2, and audit-v2 fields remain schema-dispatched without
v3 bootstrap synthesis. The producer file and lifecycle are unchanged. The
valid v3 result sets only the evidence property `launch_qualified`; causal,
collection, gameplay-policy, run-lock, study-start, and training authority all
remain false. Task 7 crash/live/tokenization work, gameplay, Java, real
CommunicationMod launch, study start, and training remain out of scope.

## Review Fix Addendum

This addendum supersedes the earlier report-hash smoke and helper-only
source-replay descriptions. No production verifier or producer file changed.

### Portable R1-R6 Bundles (Superseded)

This subsection records the intermediate synthetic-replay implementation and
is not authoritative. Its fixture-v1 manifest hashes, public-replay table, and
claim that all six identities invoked public verification are superseded in
full by `Revised Task 6.3.4 Evidence-Bounded Resolution (2026-07-19)` below.

The read-only production roots were copied byte-for-byte under
`tests/fixtures/qualification_history/`. Each manifest pins every present root
file by relative path, SHA-256, and size and explicitly records unavailable
request/result/review/audit/report/root paths. Runtime tests use only these
tracked bundles and reject any probe of the recorded external root.

| ID | Manifest SHA-256 | Root files/bytes | Public replay | Governance |
| --- | --- | ---: | --- | --- |
| r1 | `62c01426969dcbde4321ee5d1a2d7f33b3cb55bdf8e6ac341a77b86c8d81816a` | 9/57839 | v1 `sealed_invalid`, `invalid_partial`, `orphan_control_artifacts`, consumed | `failed_pre_ready`, consumed |
| r2 | `2573c8df27b80050b909e083963c38665c82ab6c4f69c01971ba820ad4131638` | 10/76965 | v1 `sealed_invalid`, `invalid_partial`, `orphan_control_artifacts`, consumed | `failed_readiness_timeout`, consumed |
| r3 | `a94fb0d39f20d1b17490a50dc787683ac3ee0f2f65bce46c5a05bb02d9b60d1e` | 11/79786 | v1 `sealed_invalid`, `invalid_partial`, `orphan_control_artifacts`, consumed | `failed_release_side`, consumed |
| r4 | `a1b74d3f51c95ce8a62a73673800f4d9f38e714b4895ca33c7f511c03ed93755` | 1/950 | v1 `reviewed_prepared`, `not_attempted`, `source_only`, not consumed | `obsolete_prepared`, not consumed |
| r5 | `0ca1377392955da2239b7138199104700168975412034f3fd5aaee4b68fad95d` | 1/949 | v2 `reviewed_prepared`, `not_attempted`, `source_only`, not consumed | `retired_pre_request`, consumed |
| r6 | `ae13c59f46ef23c9e9a968f19238fe5669702cae0c423901e4d08b627ca66185` | 1/949 | v2 `reviewed_prepared`, `not_attempted`, `source_only`, not consumed | `retired_pre_request`, consumed |

The former synthetic test called public `verify_prelock_qualification()` for
all six identities through temporary Git history. That narrative is retired:
no incomplete r1-r6 bundle is publicly replayed, and no missing request,
review, audit, or Git anchor is synthesized.

### Top-Level Source-Only V3

The fixture independently writes request, claim, five stages, active request,
handoff, attempt, ready, release, restored isolation, result, and
review-binding bytes around a real Git S/R pair. A real `-I -S` child exits zero;
its PID is bound into ready/release/result and the unpatched verifier proves it
dead. The verifier loads under `-I -S` with the producer key absent before
load, after load, and after public top-level replay. The valid chain verifies;
caller tampering of request hash/SHA/size, review commit, and result hash/SHA/
size all rejects. Audit v3 is consumed/non-retryable and all authority is false.

### Exact Review-Fix Evidence

Structural RED: `1 failed, 315 deselected`; it detected the direct audit smoke
and helper-only source replay.

```text
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "historical_r1_r6_reviewed_bytes_and_dispatch" -p no:cacheprovider --basetemp task6-history-selector-tmp -q
6 passed, 310 deselected in 39.11s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "source_only_replay_without_producer" -p no:cacheprovider --basetemp task6-source-only-tmp -q
1 passed, 315 deselected in 24.28s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py tests\test_noncombat_outcome_evidence_runner.py -k "bootstrap_terminal or historical_r1 or historical_r2 or historical_r3 or historical_r4 or historical_r5 or historical_r6" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\terminal-history-green -q
95 passed, 556 deselected in 113.22s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "complete_handoff_snapshot or cross_record_pid_drift or literal_json_damage or rehashed_wrong_previous_link or nonempty_preexisting_drift or canonical_wrong_handoff_payload or bootstrap_prefix_import_independence" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\task6-fix-task5-focused -q
26 passed, 290 deselected in 3.39s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "bootstrap_prefix or reviewed_prepared or pre_request_partial or sealed_invalid or active_request_partial or authority" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\task6-fix-prefix -q
71 passed, 245 deselected in 47.36s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "historical_schema_bytes or qualification_verifier_replays_passed_terminal_evidence or qualification_verifier_replays_v1_as_historical_unqualified_evidence or qualification_verifier_collector_matches_runner_fixture_vector or verifier_has_static_import_independence or bootstrap_prefix_import_independence or does_not_import_ordinary_audit_helpers" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\task6-fix-history-import -q
7 passed, 309 deselected in 14.08s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py tests\test_noncombat_outcome_evidence_runner.py -k "qualification_verifier_replays_passed_terminal_evidence or qualification_verifier_replays_failed_terminal_without_authority or qualification_orchestrator" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\task6-fix-focused-lifecycle -q
15 passed, 636 deselected in 57.35s

openspec validate --all --strict
Totals: 41 passed, 0 failed (41 items)

git diff --check
exit 0; this working-tree check did not inspect the then-untracked fixture
bytes and was not evidence that the staged diff was clean
```

The broader `qualification_verifier or qualification_orchestrator` command
timed out after 244.5 seconds before pytest emitted a result. It left no Python
process, is not counted as a pass, and was replaced by the exact 15-test focused
lifecycle selector above. No full-suite pass is claimed. OpenSpec 3.3 and 3.4
are checked; Task 7/live/game/start/collection/OPE/policy/causal/training work
and authority remain out of scope and false.

## Task 6 review-fix wave

The inherited patch had portable r1-r6 bundles and public replay coverage, but
the replay builder did not derive its local reviewed Git request/review paths
from the preserved request/review fixtures. The fix now pins every manifest
artifact presence/hash/size, preserves each root absence inventory, and makes
the r4-r6 local public replay use the stored request schema, request source
relative path, and ordered review allowlist. The external production roots are
rejected by the verifier path guard during every replay.

RED (the added artifact-binding assertion):

```text
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "historical_r1_r6_reviewed_bytes_and_dispatch_remain_immutable" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\task6-history-red -q
6 failed, 310 deselected in 13.42s
```

GREEN (including the short portable replay location needed for the preserved
r4-r6 Windows filenames):

```text
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "historical_r1_r6_reviewed_bytes_and_dispatch_remain_immutable" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\task6-history-green -q
6 passed, 310 deselected in 39.39s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py tests\test_noncombat_outcome_evidence_runner.py -k "bootstrap_terminal or historical_r1 or historical_r2 or historical_r3 or historical_r4 or historical_r5 or historical_r6" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\terminal-history-green -q
95 passed, 556 deselected in 111.45s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "complete_handoff_snapshot or cross_record_pid_drift or literal_json_damage or rehashed_wrong_previous_link or nonempty_preexisting_drift or canonical_wrong_handoff_payload or bootstrap_prefix_import_independence" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\task6-fix-task5-focused -q
26 passed, 290 deselected in 3.78s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "bootstrap_prefix or reviewed_prepared or pre_request_partial or sealed_invalid or active_request_partial or authority" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\task6-fix-prefix -q
71 passed, 245 deselected in 52.50s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "historical_schema_bytes or qualification_verifier_replays_passed_terminal_evidence or qualification_verifier_replays_v1_as_historical_unqualified_evidence or qualification_verifier_collector_matches_runner_fixture_vector or verifier_has_static_import_independence or bootstrap_prefix_import_independence or does_not_import_ordinary_audit_helpers" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\task6-fix-history-import -q
7 passed, 309 deselected in 15.82s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py tests\test_noncombat_outcome_evidence_runner.py -k "qualification_verifier_replays_passed_terminal_evidence or qualification_verifier_replays_failed_terminal_without_authority or qualification_orchestrator" -p no:cacheprovider --basetemp D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\task6-fix-focused-lifecycle -q
15 passed, 636 deselected in 61.88s

openspec validate --all --strict
Totals: 41 passed, 0 failed (41 items)
```

The earlier broad `qualification_verifier or qualification_orchestrator`
selector still timed out after 244.5 seconds without a pytest result; it is not
counted as a pass. No new broad suite was run. The source-only `-I -S` v3
top-level replay remains covered by the exact terminal/history selector: it
loads the verifier with the producer absent before/after loading and replay,
uses a real reviewed Git request/commit and dead child, verifies audit-v3 with
all authority false, and rejects all seven caller-anchor tamper variants.

### Staged diff correction

The earlier statements calling the diff check clean were incomplete. The
working-tree-only `git diff --check` did not include the then-untracked
historical bundles. After staging, the real check was not clean:

```text
git diff --cached --check
exit 2; only 12 preserved-byte files under r1-r4 root/** were flagged for
literal CRLF, CRCRLF, or trailing bytes
```

Those bytes are immutable fixture evidence and cannot be normalized without
breaking their pinned sizes and SHA-256 values. The fixture-local attribute is
therefore narrow: `**/root/** binary`. It preserves only root evidence
byte-for-byte and suppresses text whitespace diagnostics for those captures;
artifacts, manifests, and test source remain reviewable text.

Final staged check:

```text
git diff --cached --check
exit 0; no output
```

## Revised Task 6.3.4 Evidence-Bounded Resolution (2026-07-19)

This addendum replaces the synthetic r1-r6 reenactment proof. The manifests
now use `qualification-history-fixture-v2` and independently pin every
available portable artifact/root byte by relative path, size, and SHA-256.
Every unavailable root or artifact path is explicitly recorded with null size
and SHA-256. Tests reject reads below `D:\SteamLibrary` and do not call public
replay for an incomplete preserved bundle.

### RED

The controller ran the revised-contract RED before this implementation:

```text
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "historical_replay_uses_only_preserved_request_and_root_bytes" -p no:cacheprovider --basetemp ...\task6-revised-red -q
6 failed, 316 deselected in 12.26s
```

R1-r3 exposed generated non-null request bytes despite preserved absence.
R4-r6 exposed generated request bytes that differed from the preserved request
artifact. Those synthetic request/audit/Git reenactment helpers are retired.

### Eligibility Matrix

| Identity | Evidence classification / consumed | Governance disposition / consumed | Public v1/v2 replay | Reasons |
| --- | --- | --- | --- | --- |
| r1 | `sealed_invalid` / true | `failed_pre_ready` / true | ineligible | missing preserved request, review, and Git anchors |
| r2 | `sealed_invalid` / true | `failed_readiness_timeout` / true | ineligible | missing preserved request, review, and Git anchors |
| r3 | `sealed_invalid` / true | `failed_release_side` / true | ineligible | missing preserved request, review, and Git anchors |
| r4 | `reviewed_prepared` / false | `obsolete_prepared` / false | ineligible | missing preserved review commit and Git anchors |
| r5 | `reviewed_prepared` / false | `retired_pre_request` / true | ineligible | missing preserved Git anchors |
| r6 | `reviewed_prepared` / false | `retired_pre_request` / true | ineligible | missing preserved Git anchors |

All six remain no-retry, unlaunchable, and authority-false. R6 preserves
recorded audit hash
`938d603a13601717f26c92684e88ca35a32ec6baff51757a0351de3cb36c48a0`
as governance metadata only; its audit bytes, file SHA-256, and size are
explicitly absent. R5/r6 source-only evidence remains distinct from their
immutable governance-consumed status.

### GREEN

```text
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "historical_r1_r6 or canonical_public_v1_v2" -p no:cacheprovider --basetemp ...\task6-revised-history -q
8 passed, 308 deselected in 30.30s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "source_only_replay_without_producer" -p no:cacheprovider --basetemp ...\task6-revised-source-only -q
1 passed, 315 deselected in 24.81s

D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py tests\test_noncombat_outcome_evidence_runner.py -k "bootstrap_terminal or historical_r1 or historical_r2 or historical_r3 or historical_r4 or historical_r5 or historical_r6" -p no:cacheprovider --basetemp ...\terminal-history-root-cause -q
95 passed, 556 deselected in 70.77s

Task 5 focused: 26 passed, 290 deselected in 3.13s
Task 5 prefix/classification: 71 passed, 245 deselected in 47.20s
Task 5 history/import: 7 passed, 309 deselected in 14.56s
Focused lifecycle: 15 passed, 636 deselected in 57.17s
openspec validate --all --strict: 41 passed, 0 failed
git diff --check: exit 0
```

The immutable canonical public v1/v2 vectors remain compatibility coverage;
they are explicitly labeled as canonical vectors, not r1-r6 provenance.
No production verifier, runner, source-only v3 proof, game/configuration, or
unrelated report changed.

## Task 6 Source-Only Git Path Reliability Fix

The post-`b6c1e561a` source-only fixture placed its replay tree below the long
pytest node directory and then nested the temporary Git worktree below that
tree. On Windows, the controller's long basetemp made Git traversal of the
copied verifier source and generated bytecode exceed Git's filename budget;
public source-only replay returned `valid.kind=error` with `Filename too long`.
The verifier and Git configuration were correct and remain unchanged.

The controller-confirmed RED was:

```text
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "source_only_replay_without_producer" -p no:cacheprovider --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\task6-controller-terminal-history-extra-path-length-confirmation" -q
1 failed, 315 deselected in 5.70s
Git show: Filename too long
```

The focused layout assertion also failed under an ordinary short basetemp,
proving that the Git root was nested instead of being a direct basetemp child:

```text
D:\anaconda\envs\stsai\python.exe -m pytest tests\test_noncombat_outcome_evidence_verifier.py -k "source_only_replay_without_producer" -p no:cacheprovider --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pt\t6-git-layout-red" -q
1 failed, 315 deselected in 3.90s
```

The test-only fix creates separate unique `s-*` state and `g-*` Git worktree
directories directly under `tmp_path.parent`, which is pytest's basetemp. Each
component is asserted to be at most 12 characters, both remain entirely inside
basetemp, and `tempfile.mkdtemp()` prevents shared collisions. No global Git
`longpaths` setting, production verifier behavior, manifest, OpenSpec task, or
game/configuration file changed.

Final GREEN evidence:

```text
Exact long-basetemp source-only: 1 passed, 315 deselected in 22.69s
Exact long-basetemp terminal/history: 95 passed, 556 deselected in 65.56s
Revised historical/source-only controller gate: 9 passed, 307 deselected in 45.11s
Focused lifecycle gate: 15 passed, 636 deselected in 51.27s
openspec validate --all --strict: 41 passed, 0 failed
```
