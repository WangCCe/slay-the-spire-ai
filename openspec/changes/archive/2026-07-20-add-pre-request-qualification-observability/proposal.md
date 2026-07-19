## Why

The one-shot r6 Windows qualification launch used the reviewed runner and explicit 120-second CommunicationMod initialization timeout, but the external process produced neither `ready` nor an active request before CommunicationMod killed it. The trusted launcher and runner intentionally suppress protocol-adjacent output, while CommunicationMod does not distinguish an exited silent process from a running silent process, so the preserved evidence cannot identify which pre-request validation stage stopped.

Future qualification identities need durable, request-bound stage evidence before active-request publication. That evidence must improve diagnosis without making a partial prefix retryable or granting study, gameplay, OPE, training, policy, causal, or promotion authority.

## What Changes

- Add a pure-stdlib pre-request evidence protocol with an exclusive claim, immutable hash-linked stage records, a request handoff, fixed failure classes, and independent prefix replay.
- Treat the first successfully created claim as irreversible consumption of the qualification identity; any valid, partial, malformed, or corrupt prefix remains non-retryable and fail closed.
- **BREAKING**: require every future launchable qualification to use qualification request/result/review-binding v3 and bootstrap-evidence v1. Every actually preserved historical v1/v2 byte and every recorded absence remains immutable and read-only verifiable; only a historical bundle that retains all request, review, and Git anchors is eligible for complete public replay, and no incomplete bundle may be reconstructed. Historical evidence cannot launch or qualify a replacement.
- Bind the trusted launcher command to a deterministic launch token, claim path, ordered stage contract, reviewed runner SHA-256, request anchors, and review commit before the runner imports project code.
- Freeze the exact raw worktree bytes and opened-file identities accepted during reviewed-source validation and require every later project-source import to re-read through descriptor-bound no-follow identity checks and match both immutable bindings before code execution.
- Extend the standalone verifier to classify the last independently supported pre-request stage, validate a complete v3 handoff and terminal chain, reject gaps or mutations, and preserve the existing all-false authority boundary for every incomplete prefix.
- Add regression, subprocess crash-matrix, backward-compatibility, focused/full pytest, strict OpenSpec, byte, and source-only review gates.
- Do not change CommunicationMod, increase a timeout, retry r6, prepare r7, launch the game, collect study evidence, tune policy, or start training in this change.

Success means every injected failure after claim creation is classified from qualification-root artifacts alone, a second invocation is rejected before active request or child launch, a complete fixture independently verifies, the r1-r6 byte/absence inventory and separately recorded evidence and governance classifications remain unchanged, and protected gameplay/study isolation remains untouched.

## Capabilities

### New Capabilities
- `pre-request-qualification-observability`: Defines exclusive identity consumption, immutable launcher/runner/source/request/isolation stage evidence, active-request handoff, failure classification, and independent replay before the existing qualification handshake.

### Modified Capabilities
- `noncombat-outcome-evidence-expansion`: Requires a future replacement qualification to use and pass the v3 pre-request evidence contract before it can support any later `start` decision, while retaining historical r1-r6 as non-authorizing evidence.

## Impact

- Primary implementation: `scripts/run_noncombat_outcome_evidence_expansion.py` and `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py`.
- Regression coverage: `tests/test_noncombat_outcome_evidence_runner.py`, `tests/test_noncombat_outcome_evidence_verifier.py`, and narrowly related qualification fixtures only.
- Protocol artifacts: future qualification request/result/review-binding v3 plus bootstrap-evidence v1; no mutation of existing registration, r1-r6 root, request, terminal, audit, or report bytes.
- Runtime boundary: Windows production Python remains `D:\anaconda\envs\stsai\python.exe`; CommunicationMod stdin/stdout semantics and ordinary gameplay startup remain unchanged.
- Dependencies: Python standard library and existing Git/qualification primitives only; no new package or service.
- Rollback boundary: before any v3 claim is created, the implementation can be reverted without external study state. Once any v3 claim or stage entry exists, that root is immutable and permanently consumed even if code is reverted; it cannot be cleaned, retried, or promoted.
