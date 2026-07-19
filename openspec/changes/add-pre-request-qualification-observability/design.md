## Context

R6 was a separately reviewed, one-shot Windows qualification identity launched through real CommunicationMod with explicit `maxInitializationTimeout=120`. CommunicationMod created the external process, received no stdout readiness signal, waited the full deadline, and killed it before the qualifier published its active request. The root remained static-config-only and all request-bound isolation was restored, but the evidence cannot distinguish an immediate silent exit from a stall inside runner, source, request, review-chain, or isolation validation.

The ambiguity follows from two intentional boundaries. The trusted launcher and qualification runner suppress stdout and stderr so they cannot contaminate CommunicationMod's protocol stream, and the runner does not create a control artifact until all pre-request checks pass. CommunicationMod's reader also keeps waiting after child EOF, so an exited silent process and a running silent process have the same external timeout symptom.

The current qualification protocol already provides exclusive active-request, attempt, ready, release, terminal, isolation, and independent-verifier evidence. This change extends that model earlier without changing CommunicationMod, ordinary gameplay, the registered study, or the authority of the existing handshake.

## Goals / Non-Goals

**Goals:**

- Consume a future qualification identity at the first durable bootstrap claim rather than at active-request publication.
- Preserve one immutable, request-bound stage prefix from trusted-launcher entry through prelaunch-isolation validation.
- Let an independent verifier identify the last completed stage or fixed failure class using qualification-root artifacts alone.
- Bind a complete pre-request prefix into active-request handoff, terminal evidence, and independent attestation.
- Preserve CommunicationMod stdin/stdout compatibility, request-bound isolation, no-retry behavior, and uniformly false study/training/policy authority for every incomplete prefix.
- Preserve every actually available r1-r6 request/result/review/audit/report/root byte, explicitly preserve every unavailable artifact as absent, and keep evidence-derived classification separate from any externally reviewed governance disposition. Require complete public v1/v2 replay only when the preserved bundle contains every request, review, and Git anchor required by that public path.

**Non-Goals:**

- Retrospectively diagnose, relabel, retry, repair, or promote r6.
- Increase CommunicationMod or handshake timeouts.
- Modify CommunicationMod Java code or rely on its global stderr log as authoritative evidence.
- Prepare or launch r7, invoke the game, create a study run lock, collect trajectories, run OPE, change gameplay policy, or train a model.
- Generalize the evidence writer into an application-wide logging framework.

## Decisions

### 1. Use a v3 qualification contract with a separate bootstrap-evidence v1 schema

Every future launchable qualification request, review binding, and result will use v3 and will bind one `qualification-bootstrap-evidence-v1` contract. Request v3 will declare the guarded qualification root, fixed direct-child claim/stage/failure/handoff paths, ordered stage names, token derivation inputs, and authority rules. Result v3 will bind the observed bootstrap inventory, final stage hash, and handoff hash.

Historical request/result v1/v2 parsing remains in a separate read-only verifier branch. The runner will reject those versions for a new launch.

Historical compatibility is bounded by the bytes that survived. R1-r3 do not retain request, result, review, or audit bytes; r4 has no review commit; r6 records an audit hash without audit bytes; and source-only bundles may retain a governance retirement decision that is not derivable from root artifacts alone. Tests will therefore pin every available byte by path, size, and SHA-256, pin an explicit absence inventory, and record evidence-derived classification separately from the immutable governance disposition. They will invoke the complete public v1/v2 verifier only for bundles that preserve all required anchors. They must not render a substitute request, invent a review commit, reconstruct audit bytes from a hash, or report a governance decision as if it were root-derived evidence.

Alternative considered: add optional observability fields to request v2. Rejected because optional fields would make the consumption boundary ambiguous and could permit a future launch to omit the new contract while still appearing v2-valid.

### 2. Publish an exclusive claim before every other pre-request stage

The trusted launcher will receive fixed-position bootstrap anchors alongside the reviewed runner path/SHA and qualification CLI arguments. Those anchors derive one deterministic launch token from the qualification identity, guarded root and artifact names, request self-hash/file-SHA/size, external review commit R, reviewed runner SHA-256, and schema versions.

After validating only the minimum local absolute no-follow root and claim path needed to write safely, the trusted launcher will create the claim with exclusive creation and durable flush. Any claim entry, including a malformed or partially written one, consumes the identity. The publisher will never truncate, replace, delete, or complete an existing claim.

If an externally observed launch produces no claim, the evidence remains non-authorizing and the operator must conservatively retire that identity. Absence is not proof that no process was created.

Alternative considered: create the claim in an external operator wrapper before Java launch. Rejected because it would reintroduce a second owner and a race between configuration application, game launch, and qualifier execution.

### 3. Use immutable hash-linked stage files, not an append-only journal

After the claim, the same qualification process will exclusively publish these ordered stages:

1. `launcher_verified`: runner path, runner bytes, launcher shape, and static bootstrap anchors passed.
2. `runner_entered`: the in-memory runner verified isolated/no-site execution, original argv, and launcher environment anchor.
3. `source_verified`: the pre-import Git metadata, HEAD/R, reviewed executable/importable bytes, tracked inventory, and untracked executable checks passed, and the exact accepted raw worktree bytes plus opened-file identities were installed as immutable source-only import bindings.
4. `request_reviewed`: argument parsing, canonical request source, external request anchors, S-to-R review chain, registration, and implementation map passed.
5. `isolation_verified`: request-bound CommunicationMod semantics and broad marker/run/checkpoint/global-log isolation passed immediately before active-request publication.

Each canonical ASCII JSON record will contain the schema, qualification identity, launch token, stage index/name, process PID, positive timestamp, previous-record hash, static request/R/runner anchors, and its own self-hash. Static anchors must remain identical across the chain. A controlled failure may add one exclusive failure record containing the last completed stage, a fixed failure code, exception type, optional errno/winerror, and bounded sanitized detail. It must not include environment values, arbitrary process output, gameplay outcomes, or secrets.

The earliest writer remains pure standard library and independent of project imports. Later code may use the same small primitive but may not rewrite earlier evidence. Temporary, duplicate, out-of-order, non-canonical, malformed, or extra entries make the root consumed and invalid.

Publishing `source_verified` does not permit later imports to trust the path that was previously checked. The source-only repository loader must re-read each requested source through a no-follow descriptor, verify the opened file identity across the read, and compare both the returned bytes and opened-file identity exactly with the immutable values captured during reviewed-source validation. A replaced, linked, unbound, identity-drifted, or byte-drifted source therefore stops before module code executes and leaves `source_verified` as the last valid stage at most.

Alternative considered: append JSONL records to one journal. Rejected because mutation, torn tails, append races, and recovery semantics would make independent replay materially harder than fixed publish-once artifacts.

### 4. Bind the pre-request chain to the existing active request with a handoff

Request v3 statically binds every bootstrap path, stage name, schema, and launch-token derivation input. After `isolation_verified`, the qualifier publishes the exact reviewed active-request bytes using the existing exclusive operation. It then publishes one bootstrap handoff that binds the claim hash, ordered final stage hash, active-request byte SHA-256, request self-hash, and launch token.

A crash between active-request publication and handoff remains an immutable active-request partial. It cannot be repaired or relabeled. Attempt publication and child launch remain forbidden until the handoff is valid. Completion/failure result v3 and its review binding will include the independently reconstructable bootstrap inventory and handoff hash.

Alternative considered: place a runtime stage hash inside the precommitted active-request bytes. Rejected because that would require mutating reviewed request bytes or predicting runtime PID/time/hash fields.

### 5. Keep stdout, stderr, child ownership, and live restoration boundaries unchanged

The launcher and qualifier will remain silent on CommunicationMod stdout and stderr. Stage evidence uses only guarded qualification-root files. The qualifier will still launch at most one registered no-action child after active request, handoff, and attempt publication, and will continue forwarding the child's stdin/stdout/stderr exactly as before.

Pre-request observability does not move CommunicationMod restoration ownership earlier. If the qualifier stops before it can own restoration under the reviewed request, the controlled operator path must stop Java, restore exact baseline bytes, and independently recollect isolation. The bootstrap prefix records where execution stopped but cannot claim restoration or live cleanliness.

Alternative considered: emit diagnostics to `communication_mod_errors.log`. Rejected because prior log-sharing behavior, global append state, and lack of request/chain binding make it supplemental rather than authoritative.

### 6. Extend the independent verifier with explicit v3 prefix states

Without importing producer result builders, the verifier will independently reconstruct the launch token and expected path set from S/R/request/external anchors, inspect every entry no-follow, validate canonical bytes and the hash chain, and classify exactly one state:

- `reviewed_prepared`: no claim and no bootstrap/control artifact; not consumed and not launch evidence.
- `pre_request_partial`: valid claim and contiguous stage prefix, with an optional valid failure record; consumed and non-authorizing.
- `sealed_invalid`: malformed claim, gap, mutation, collision, unexpected entry, inconsistent anchors, invalid failure, or other corrupt prefix; consumed and non-authorizing.
- `active_request_partial`: valid pre-request prefix and active request but missing or invalid handoff/attempt/terminal; consumed and non-authorizing.
- existing verified terminal branches, available only after exact v3 handoff and lifecycle replay.

An abrupt process stop without a failure record is reported as `abrupt_after_<last-stage>`. A valid failure record uses a fixed failure class. No pre-request state can authorize `start`, collection, OPE, training, gameplay-policy changes, causal claims, or promotion.

Alternative considered: treat bootstrap files as operator diagnostics outside independent verification. Rejected because unbound diagnostics would not close the evidence gap that blocked r6.

### 7. Keep implementation and validation offline in this change

Implementation will start from red unit and subprocess regressions, then add the producer contract, independent verifier branch, crash matrix, and evidence-bounded historical compatibility checks. The change will not edit live CommunicationMod configuration or create a new qualification root. A separate reviewed amendment may prepare a future identity only after this change passes source-only review.

## Risks / Trade-offs

- [The process can stop while writing the first claim] -> Any claim-path entry consumes the identity; the verifier classifies malformed bytes as `sealed_invalid` rather than treating the root as retryable.
- [Python can fail before executing the trusted launcher] -> No internal artifact can prove an unexecuted process; retain the external CommunicationMod/process boundary and conservatively retire any externally observed launch without a claim.
- [Additional file writes increase cold-start time] -> Keep records small, bounded, and publish-once; do not repeat full Git, source, inventory, or isolation scans merely to render a stage record.
- [The bootstrap command grows] -> Pass compact fixed anchors and a deterministic token, not request JSON or diagnostic text, and retain CommunicationMod-equivalent tokenization tests.
- [Early diagnostics could expose sensitive state] -> Use fixed failure codes and bounded sanitized exception metadata; forbid environment values, stdout/stderr capture, gameplay outcomes, and arbitrary file content.
- [Pure-stdlib publication duplicates an existing helper] -> Keep one minimal bootstrap primitive, test its bytes and path behavior directly, and reuse it after imports rather than maintaining divergent formats.
- [A repository path can change after source validation but before import] -> Freeze the exact descriptor-read raw bytes and opened-file identity before publishing `source_verified`; require every source-only import to perform another descriptor-bound no-follow read and exact identity-plus-byte comparison before compilation.
- [v3 support could change historical evidence or blur a governance decision into root-derived proof] -> Isolate the v3 branch, require exact r1-r6 byte and absence inventories, keep evidence and governance classifications distinct, and run complete public replay only for historically complete bundles.
- [A valid prefix can still lack exact root cause after abrupt termination] -> Report only the last independently completed stage; do not infer the in-progress operation or use offline timing as live proof.

## Migration Plan

1. Add red schema, exclusive-claim, path-safety, canonical-chain, stream-silence, crash-prefix, handoff, authority, and historical byte/absence compatibility regressions.
2. Implement the pure-stdlib bootstrap claim/stage primitive and v3 request construction/loading without changing v1/v2 historical readers.
3. Integrate trusted-launcher, runner-entered, source, request, isolation, active-request, handoff, and terminal bindings while preserving the existing child ownership and restoration paths.
4. Implement independent v3 prefix/terminal replay without importing producer result builders.
5. Run focused producer/verifier tests, the complete Windows pytest suite, strict OpenSpec validation, byte/whitespace checks, and independent source-only review.
6. Update the pending observability tasks in the orchestrator and v2 study changes only after this implementation is reviewed; do not prepare a replacement root in the same change.
7. In a separate amendment, freeze a new source snapshot and prepare a previously absent future qualification identity using request v3.

Before any v3 claim exists, rollback is an ordinary code revert. Once a claim or stage entry exists, that external root must be preserved forever and cannot be made retryable by rollback, cleanup, schema downgrade, or verifier reinterpretation.

## Open Questions

None. The identity-consumption boundary, artifact model, v3 compatibility rule, authority limits, and offline-only validation scope were explicitly reviewed before this proposal was written.
