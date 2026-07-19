# Pre-Request Qualification Observability Offline Closeout

Date: 2026-07-20

## Scope And Source Range

This closeout covers the source-only implementation range
`b4487b6f039cc92a1f5caa69d269e043f35a3771..bef034c064c570f5db51684e95e2d39b38f46693`
plus the Task 8 compatibility regressions, reviewed-source correction,
reproducible vector renderer, OpenSpec correction, and evidence files listed
in Appendix A.

The range contains 25 cohesive commits. It adds durable pre-request evidence,
independent replay, historical evidence fixtures, and offline compatibility
proof. It does not create or authorize a replacement qualification identity.

The exact source-range paths are listed in Appendix A. The committed
implementation range remains fixed; Task 8 binds its uncommitted correction
and closeout evidence to exact file hashes before the cohesive closeout commit.

## Frozen Schemas And Artifacts

The current schemas are:

- request: `noncombat-outcome-evidence-qualification-request-v3`
- result: `noncombat-outcome-evidence-qualification-result-v3`
- review binding: `noncombat-outcome-evidence-qualification-review-binding-v3`
- bootstrap evidence: `noncombat-outcome-evidence-qualification-bootstrap-evidence-v1`
- bootstrap token: `noncombat-outcome-evidence-qualification-bootstrap-token-v1`

Historical request/result v1 and v2 and review-binding v1 remain immutable,
replay-only contracts. Current request v3 uses these fixed direct-child names:

- `qualification-bootstrap-claim.json`
- `qualification-bootstrap-stage-01-launcher-verified.json`
- `qualification-bootstrap-stage-02-runner-entered.json`
- `qualification-bootstrap-stage-03-source-verified.json`
- `qualification-bootstrap-stage-04-request-reviewed.json`
- `qualification-bootstrap-stage-05-isolation-verified.json`
- `qualification-bootstrap-failure.json`
- `qualification-request.json`
- `qualification-bootstrap-handoff.json`

The active request is published only after the five-stage prefix. The handoff
binds the claim hash, final-stage hash, active-request file hash and size, and
request self-hash. Claim publication consumes the identity permanently.

Before `source_verified`, reviewed-source validation reads each executable or
importable worktree path through a no-follow descriptor, validates it against
R, and freezes the exact accepted raw bytes and opened-file identity in
immutable import bindings. Every later project-source import repeats the
descriptor identity checks and requires exact identity and byte equality before
compilation. A replaced, linked, unbound, identity-drifted, or byte-drifted
source stops before module code executes and can leave at most an
`abrupt_after_source_verified` prefix; restoring the path later cannot make an
active request, child, or terminal evidence valid.

## Fixed Byte And Hash Evidence

The final compatibility-vector identities are:

| Vector | Bytes | File SHA-256 |
| --- | ---: | --- |
| request v1 | 5996 | `fedb4c8d0fdf7d7f2c211455a42a794f0bddf18a7b392b62de89da8032f61936` |
| request v2 | 8886 | `28c174d6fba875ba110b107c92da5d522664ead81d9bf5c0db71db6fc3748b69` |
| request v3 | 10700 | `285698c9726312fc6631fd69fd1216ba65be028376439c2baa673c87c61fa662` |
| result v1 | 6848 | `15bebc995815380d9adaed69533fd3d370763e6775c9f9298f51781a45186349` |
| result v2 | 7184 | `401272257f085a23e17c62752e312d0dad5b0ba96d3d7982e1258f28285a9a86` |
| result v3 | 7191 | `f8599566b724f652900c2756aa25469bd13db716d7635d1fca67c667cdf8c19b` |
| review binding v1 | 2094 | `1e68c9c609e870107f47cf8484639420db26b7331288fc1e1b70b89a2833e044` |
| review binding v3 | 2096 | `5ac5716b1f08c75cbef6e6f9b969c3cddd24ae2dfc442e1882d530495d5e8441` |

The producer bootstrap vector has canonical envelope SHA-256
`601d300a7f67a82b6f44495a488228e4366135d5591cb1ce3176e0645a29322e`
over 1734 bytes and launch token
`6f21f2b4324bea5277ef12e03b87e2ab84f3ead09b1def0fda52d3f201aa4089`.
The verifier's independent lexical-root vector has canonical envelope SHA-256
`926af6b9addd083e2127050d09947d58e714aaa590988354b3639c0487c3aa42`
over 1617 bytes and launch token
`17ba93387ea9ac596ab0a8b4fddcd3838b2ad11d3ed8fb2f5d8d83834ef6d34f`.

The tracked renderer
`analysis_scripts/render_pre_request_qualification_observability_vectors.py`
validates the fixed protocol vectors, each preserved r1-r6 file, and every
declared absence before framing 73 named entries. Two fresh Windows Python
processes produced byte-identical 11158-byte JSON outputs with SHA-256
`9d4e3a7ee727e4668b331960492b080fc7e12bc6db393851556b3ad2137c4533`.
The framed payload is 434459 bytes and has SHA-256
`f3f493b9ed767405ee5f23660af512c603b7107857e811f8ea2b21951bbaad3f`.

The independent source-only terminal fixture remains pinned to:

| Field | Value |
| --- | --- |
| request self-hash | `4a64dbe193b981fda14043c0c98f3a5c2af3c11c1430a0df7909381029bc41ce` |
| request file SHA-256 / size | `e0e943bf9a63b7d6534a247fadd6af2933b3408ba92672895778cbe27f325198` / 6425 |
| result self-hash | `beae07fde11c2fe4bb8a2bdfa5fd0e0a74c44f505664ea3a8f9c2aadadc40fa2` |
| result file SHA-256 / size | `39ed870033f34c84917af47a0a3949c14641053387e611cb69e5b606052b64b3` / 8968 |
| review binding self-hash | `1099d574ee333e3233615b2203b097c11669ec2dfa9852d057e6da1ab35c06c7` |
| claim hash | `6fd39b36efd1eb701da3cd7c57453cab6443134ac9cfdb751bde39801af6aad8` |
| final stage hash | `28315f1f8bd175ea2fb098b8f0f56da85d7ef2a68aae7b11693febabece98c9c` |
| handoff hash | `735927f23212ba65c5e30451e8831ba9536b22e7359f2c54d61ac6c28d92cc82` |
| launch token | `120c25e4f59acae54db3e86128ae9225f4ea09285084cd1594b0a3774e9ddae2` |

## Crash And Failure Matrix

The subprocess crash matrix exits with `os._exit(97)` immediately after each
durable boundary and replays the remaining bytes in a separate verifier
process:

| Durable stop | Classification | Last or partial stage |
| --- | --- | --- |
| claim | `pre_request_partial` | `abrupt_after_claim` |
| launcher verified | `pre_request_partial` | `abrupt_after_launcher_verified` |
| runner entered | `pre_request_partial` | `abrupt_after_runner_entered` |
| source verified | `pre_request_partial` | `abrupt_after_source_verified` |
| request reviewed | `pre_request_partial` | `abrupt_after_request_reviewed` |
| isolation verified | `pre_request_partial` | `abrupt_after_isolation_verified` |
| active request before handoff | `active_request_partial` | `missing_handoff` |
| complete handoff before attempt | `handoff_complete` | none |

Every prefix is consumed, non-retryable, and non-authorizing. A second launch
for every consumed prefix exits 2 with empty stdout and stderr and leaves the
canonical recursive inventory unchanged.

Controlled failures are fixed to the last successfully published boundary:

| Rejection boundary | Last valid stage | Failure code |
| --- | --- | --- |
| launcher runner path/hash/vector | claim | `runner_validation_failed` when a bounded record can be published |
| runner isolated/no-site/argv/environment/current bytes | launcher verified | `runner_entry_validation_failed` |
| Git/HEAD/reviewed source/tracked/importable inventory | runner entered | `source_validation_failed` |
| request/review/registration/implementation/command | source verified | `request_validation_failed` |
| CommunicationMod/marker/run/checkpoint/log isolation | request reviewed | `prelaunch_isolation_failed` |
| unexpected exception with a valid prefix | current valid stage | `unexpected_pre_request_failure` |

Missing or torn failure records, malformed claim bytes, stage gaps,
reordering, hash drift, duplicate and extra entries, PID drift, invalid
handoff, active request without handoff, and result/review summary laundering
all fail closed without repair or synthetic evidence.

## CommunicationMod, Streams, And Isolation

The Java-Properties-equivalent serializer/parser round-trips the exact
whitespace-split launcher vector. Trusted code, reviewed runner path and hash,
canonical envelope, launch token, mode, paths, hashes, sizes, and review commit
remain individual whitespace-free tokens.

All trusted-launcher success and controlled-failure subprocesses capture empty
binary stdout and stderr. After handoff, the one no-action child retains the
registered inherited stdio ownership. Ordinary gameplay, eval, training,
audit, monitor, dry-run, run-next, and start argument paths create no bootstrap
artifacts.

The production Windows Python smoke removes inherited
`PYTHONDONTWRITEBYTECODE`, launches the reviewed parent without `-B`, reaches a
passed terminal through a request-v3 child whose command contains fixed
`-I -S -B`, restores the fixture CommunicationMod configuration byte-for-byte,
and leaves no repository `.pyc`. It does not launch Java or the game.

Every pre-request boundary preserves exact before/after bytes for the
CommunicationMod fixture, AI marker and run tree, checkpoints, global logs,
registered study root, run lock, ledger, manifest, trace, model, and policy.
Sentinels prove zero calls to start, ledger construction, registered-slot
claim/launch, RL component loading, agent creation, and checkpoint backup.
The terminal smoke records exactly one child launch, zero exit, and no
surviving child process.

## Historical R1-R6 Evidence

The tracked fixture manifests pin each available byte by relative path, size,
and SHA-256 and pin each unavailable path as an absence. Evidence-derived
classification remains separate from immutable governance disposition.

| ID | Manifest self-hash | Root files / root bytes | Eligible public replay | Evidence classification | Governance |
| --- | --- | ---: | --- | --- | --- |
| r1 | `62c01426969dcbde4321ee5d1a2d7f33b3cb55bdf8e6ac341a77b86c8d81816a` | 9 / 57839 | no | v1 `sealed_invalid`, `orphan_control_artifacts`, consumed | `failed_pre_ready`, consumed |
| r2 | `2573c8df27b80050b909e083963c38665c82ab6c4f69c01971ba820ad4131638` | 10 / 76965 | no | v1 `sealed_invalid`, `orphan_control_artifacts`, consumed | `failed_readiness_timeout`, consumed |
| r3 | `a94fb0d39f20d1b17490a50dc787683ac3ee0f2f65bce46c5a05bb02d9b60d1e` | 11 / 79786 | no | v1 `sealed_invalid`, `orphan_control_artifacts`, consumed | `failed_release_side`, consumed |
| r4 | `a1b74d3f51c95ce8a62a73673800f4d9f38e714b4895ca33c7f511c03ed93755` | 1 / 950 | no | v1 `reviewed_prepared`, source-only, not consumed | `obsolete_prepared`, not consumed |
| r5 | `0ca1377392955da2239b7138199104700168975412034f3fd5aaee4b68fad95d` | 1 / 949 | no | v2 `reviewed_prepared`, source-only, not consumed | `retired_pre_request`, consumed |
| r6 | `ae13c59f46ef23c9e9a968f19238fe5669702cae0c423901e4d08b627ca66185` | 1 / 949 | no | v2 `reviewed_prepared`, source-only, not consumed | `retired_pre_request`, consumed |

No incomplete r1-r6 bundle is publicly replayed. No missing request, review,
audit, result, Git anchor, or runtime evidence is synthesized. The separate
complete source-only v3 fixture is eligible for public top-level replay and
verifies with the producer absent from `sys.modules`; it is not a historical
identity and grants no authority.

## Verification Results

Direct reviewed-source correction gates:

```text
post-validation byte and identity replacement: 4 passed, 389 deselected
runner qualification slice: 181 passed, 212 deselected in 327.38s
```

Exact focused command:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest tests/test_noncombat_outcome_evidence_runner.py tests/test_noncombat_outcome_evidence_verifier.py tests/test_main_runtime_errors.py tests/test_study_handshake.py -k "qualification or bootstrap or handshake or runtime_error" -p no:cacheprovider --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\focused-final" -q
```

Result: `593 passed, 172 deselected in 830.97s (0:13:50)`.

Exact full command:

```powershell
D:\anaconda\envs\stsai\python.exe -m pytest -p no:cacheprovider --basetemp "D:\PycharmProjects\slay-the-spire-ai\.pytest-tmp-pre-request-observability\full-final" -q
```

Result: `3455 passed in 1518.67s (0:25:18)`.

Durable pytest evidence:

| Suite | Transcript bytes | Transcript SHA-256 | Input stability |
| --- | ---: | --- | --- |
| focused | 5192 | `ce89443d13d0075fccf969614151730b469e25453ecfdd4a0850dad80002f74b` | unchanged |
| full | 9954 | `3b8c10a005c277bc978189d3c92cb454427c579a9d43867224296e73e4636dee` | unchanged |

Both LF-normalized transcripts contain the exact command, HEAD, six input file
hashes, pytest stdout/stderr, exit code, and post-run input hashes. The
machine-readable summary is
`reports/pre_request_qualification_observability_20260720_verification_evidence.json`.

Exact fresh-process render commands:

```powershell
D:\anaconda\envs\stsai\python.exe -I -B analysis_scripts\render_pre_request_qualification_observability_vectors.py --output reports\pre_request_qualification_observability_20260720_vector_render_1.json
D:\anaconda\envs\stsai\python.exe -I -B analysis_scripts\render_pre_request_qualification_observability_vectors.py --output reports\pre_request_qualification_observability_20260720_vector_render_2.json
```

Structural results:

- `openspec validate --all --strict`: 41 passed, 0 failed.
- `git diff --check`: exit 0; only line-ending conversion warnings.
- fresh-process deterministic render: byte-identical, 73 entries, 434459-byte
  bundle, SHA-256
  `f3f493b9ed767405ee5f23660af512c603b7107857e811f8ea2b21951bbaad3f`.
- case-sensitive stale-marker scan over every edited text file: clean.
- staging hygiene before review: the index contains only the intended source,
  test, OpenSpec, and closeout evidence paths; no generated bytecode, pytest
  cache, temporary root, live request/report, game output, model, policy, or
  training artifact is staged.
- independent source-only review: the first external CLI review found one P2
  same-byte file-identity replacement gap. A red subprocess regression proved
  it, the binding was extended to validation-time identity plus bytes, and the
  final CLI re-review reported no findings. The finding and clean re-review
  transcripts are stored as deterministic gzip files; both compressed and
  decompressed text hashes are bound in the verification evidence JSON.
- whole-closeout review found one additional P2 in the tracked vector renderer:
  an output beneath its scratch fixture root was written and then deleted while
  the command reported success. A red CLI regression reproduced the behavior,
  the renderer now rejects overlapping output before cleanup, the direct test
  passes, and the corrected full suite reports 3455 passing tests.

## Non-Goals, Authority, And Rollback

This change does not prepare r7 or any replacement identity. It does not edit
the live CommunicationMod configuration, launch Java or Slay the Spire, invoke
qualification through the real mod, publish a live request/root, start the
registered study, collect trajectories, compute OPE, change gameplay policy,
train a model, make a causal claim, or promote anything.

The following authority remains uniformly false in every prefix, terminal,
audit, and historical replay:

- collection
- causal claim
- gameplay policy change
- run-lock creation
- study start
- training

r7, game launch, `start`, collection, OPE, policy, causal, training, and
promotion authority require a separate explicit amendment and independent
review.

Rollback is source-only: revert the 25-commit implementation range and its
closeout commit. Historical fixture bytes are evidence and must not be edited
in place. No live cleanup, game rollback, checkpoint restoration, or model
rollback is required because this change created none of those states.

## Appendix A: Exact Modified Paths

Core implementation, planning, and tests:

```text
.superpowers/sdd/task-3-report.md
.superpowers/sdd/task-6-report.md
analysis_scripts/verify_noncombat_outcome_evidence_expansion.py
analysis_scripts/render_pre_request_qualification_observability_vectors.py
docs/superpowers/plans/2026-07-18-pre-request-qualification-observability.md
openspec/changes/add-pre-request-qualification-observability/design.md
openspec/changes/add-pre-request-qualification-observability/proposal.md
openspec/changes/add-pre-request-qualification-observability/specs/noncombat-outcome-evidence-expansion/spec.md
openspec/changes/add-pre-request-qualification-observability/specs/pre-request-qualification-observability/spec.md
openspec/changes/add-pre-request-qualification-observability/tasks.md
scripts/run_noncombat_outcome_evidence_expansion.py
tests/test_noncombat_outcome_evidence_runner.py
tests/test_noncombat_outcome_evidence_verifier.py
tests/test_pre_request_qualification_vector_renderer.py
```

Historical fixture paths:

```text
tests/fixtures/qualification_history/.gitattributes
tests/fixtures/qualification_history/r1/artifacts/report.md
tests/fixtures/qualification_history/r1/manifest.json
tests/fixtures/qualification_history/r1/root/approved-study-launch-communication.properties
tests/fixtures/qualification_history/r1/root/communication-config-before.bin
tests/fixtures/qualification_history/r1/root/communication-config-observed-smoke.bin
tests/fixtures/qualification_history/r1/root/pre-smoke-snapshot.json
tests/fixtures/qualification_history/r1/root/qualification-ai-debug.log
tests/fixtures/qualification_history/r1/root/qualification-communication-attempt.json
tests/fixtures/qualification_history/r1/root/qualification-failure-record.json
tests/fixtures/qualification_history/r1/root/qualification-smoke-communication.properties
tests/fixtures/qualification_history/r1/root/qualification-smoke-config.json
tests/fixtures/qualification_history/r2/artifacts/report.md
tests/fixtures/qualification_history/r2/manifest.json
tests/fixtures/qualification_history/r2/root/approved-study-launch-communication.properties
tests/fixtures/qualification_history/r2/root/communication-config-before.bin
tests/fixtures/qualification_history/r2/root/communication-config-observed-smoke.bin
tests/fixtures/qualification_history/r2/root/pre-smoke-snapshot.json
tests/fixtures/qualification_history/r2/root/qualification-ai-debug.log
tests/fixtures/qualification_history/r2/root/qualification-communication-attempt.json
tests/fixtures/qualification_history/r2/root/qualification-failure-record.json
tests/fixtures/qualification_history/r2/root/qualification-slay-the-spire.log
tests/fixtures/qualification_history/r2/root/qualification-smoke-communication.properties
tests/fixtures/qualification_history/r2/root/qualification-smoke-config.json
tests/fixtures/qualification_history/r3/artifacts/report.md
tests/fixtures/qualification_history/r3/manifest.json
tests/fixtures/qualification_history/r3/root/approved-study-launch-communication.properties
tests/fixtures/qualification_history/r3/root/communication-config-before.bin
tests/fixtures/qualification_history/r3/root/communication-config-observed-smoke.bin
tests/fixtures/qualification_history/r3/root/pre-smoke-snapshot.json
tests/fixtures/qualification_history/r3/root/qualification-ai-debug.log
tests/fixtures/qualification_history/r3/root/qualification-communication-attempt.json
tests/fixtures/qualification_history/r3/root/qualification-communication-ready.json
tests/fixtures/qualification_history/r3/root/qualification-failure-record.json
tests/fixtures/qualification_history/r3/root/qualification-slay-the-spire.log
tests/fixtures/qualification_history/r3/root/qualification-smoke-communication.properties
tests/fixtures/qualification_history/r3/root/qualification-smoke-config.json
tests/fixtures/qualification_history/r4/artifacts/request.json
tests/fixtures/qualification_history/r4/artifacts/review.md
tests/fixtures/qualification_history/r4/manifest.json
tests/fixtures/qualification_history/r4/root/qualification-config.json
tests/fixtures/qualification_history/r5/artifacts/request.json
tests/fixtures/qualification_history/r5/artifacts/review.md
tests/fixtures/qualification_history/r5/manifest.json
tests/fixtures/qualification_history/r5/root/qualification-config.json
tests/fixtures/qualification_history/r6/artifacts/report.md
tests/fixtures/qualification_history/r6/artifacts/request.json
tests/fixtures/qualification_history/r6/artifacts/review.md
tests/fixtures/qualification_history/r6/manifest.json
tests/fixtures/qualification_history/r6/root/qualification-config.json
```

Task 8 closeout and evidence paths:

```text
reports/pre_request_qualification_observability_20260718_closeout.md
reports/pre_request_qualification_observability_20260720_focused_pytest.txt
reports/pre_request_qualification_observability_20260720_full_pytest.txt
reports/pre_request_qualification_observability_20260720_independent_code_review_final.txt.gz
reports/pre_request_qualification_observability_20260720_independent_code_re_review_final.txt.gz
reports/pre_request_qualification_observability_20260720_vector_render_1.json
reports/pre_request_qualification_observability_20260720_vector_render_2.json
reports/pre_request_qualification_observability_20260720_verification_evidence.json
openspec/changes/add-pre-request-qualification-observability/tasks.md
openspec/changes/add-tracked-outcome-qualification-orchestrator/tasks.md
openspec/changes/run-v2-known-propensity-outcome-evidence-study/tasks.md
```
