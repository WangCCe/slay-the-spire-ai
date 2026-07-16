## Context

The immutable 2026-07-15 v1 study stopped fail-closed after slot 14 and now passes the independent blocked-closeout verifier. The recovery change added registration-v2 generation, an attempt/ready/release handshake with the real CommunicationMod child, v1 launch refusal, and independent normal/blocked verification. It deliberately created no new registration and authorized no collection.

The unresolved question is still evidence sufficiency. The frozen B3-B7 pool has only one victory and zero deterministic-Current weight on that victory, while the blocked v1 study cannot contribute a selectively recovered pool. The repository therefore needs one fresh, immutable study instance that uses the already reviewed v2 implementation without changing the behavior policy, target, estimator, thresholds, or authority boundary.

The candidate study identity is fixed as:

- Study ID: `noncombat-outcome-evidence-expansion-20260716-v2`
- Registration: `reports/noncombat_outcome_evidence_expansion_20260716_v2_registration.json`
- Artifact root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2`
- Active qualification root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r2`
- Preserved failed qualification root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification`
- Failed qualification record self-hash: `ccd76824c90a9726c57b48a7f71d8bc1d8da94df6c686ae36eff10a1b72db41f`
- Failed qualification record file SHA-256: `0677212e139270219be597e26f9e79bab30ab2c74fc5c810c41360c2d7dd545a`
- Seed base: `2026071600`

The registered study root and active replacement qualification root must be absent before their respective procedures begin. The original qualification root is intentionally present and immutable after an external PowerShell monitor stopped the first attempt before ready/release. Its failure record proves that the study root, run lock, ledger, ready, release, gameplay evidence, marker mutation, checkpoint mutation, and surviving processes remained absent and that the CommunicationMod baseline was restored byte-for-byte. Any unreviewed collision still stops this change rather than silently choosing another path or seed.

## Goals / Non-Goals

**Goals:**

- Produce and independently review one canonical registration-v2 artifact with 24 ordered 25-game slots and a new evidence root.
- Qualify the exact candidate registration and registration-bound implementation before creating the run lock.
- Execute collection blindly with the existing launch-at-most-once handshake, fixed schedule, fixed behavior distribution, and no tracked source edits.
- Produce exactly one independently verified normal or blocked closeout and preserve all source evidence.
- Decide only whether the registered evidence is ready, inconclusive, or blocked.

**Non-Goals:**

- Do not reuse, resume, repair, extend, pool, or rewrite any v1 study artifact.
- Do not change gameplay policy, exploration rates, executable alternatives, target policy, OPE estimator, bootstrap, evidence thresholds, or promotion gates.
- Do not train, tune, redesign rewards or RL spaces, execute Bottled actions live, or authorize policy promotion.
- Do not fix an implementation defect inside the frozen study. A defect requires a separate regression-backed change and a newly reviewed registration.

## Decisions

### 1. Reuse the reviewed v2 implementation without runtime edits

The change will use the current registration builder, dry-run, run-lock, ledger, handshake, monitor, finalizer, and standalone verifier. Implementation files are read-only inputs to this study. Registration generation tests may assert exact bytes, but no gameplay or analysis code is expected to change.

If registration replay, dry-run, the no-action smoke, focused tests, full tests, or independent review exposes a defect, the study will not start. The defect will be handled in a separate OpenSpec change with a red regression; this change can be revised only after that fix and a fresh registration review.

The first qualification attempt did not expose such a defect. The registered child reached coordinator construction, but an external PowerShell `File.ReadAllText` monitor treated a transient Windows log sharing violation as fatal before the child published ready. The tracked runtime implementation and canonical registration remain unchanged, so this reviewed amendment changes only the external qualification identity and monitoring procedure.

Alternative considered: repair small defects inline and retain the same candidate registration. Rejected because the registration and qualification evidence would no longer describe the source that generated them.

### 2. Freeze one new study identity and preserve the v1 boundary

The v2 registration will use the fixed identity above, schema v2, the Windows production Python, the existing 24-by-25 schedule, `card_reward=300` basis points, `shop=1000` basis points, two alternative attempts per run, deterministic Current, and the existing thresholds and estimator calibration. Slot IDs and seeds derive only from the fixed study ID and seed base.

The registration, successful replacement qualification, run lock, ledger, configs, traces, manifests, pool, estimates, and closeout will reference only the v2 candidate. The preserved failed qualification root is pre-lock operational evidence and can never enter the v2 pool or satisfy a launch gate. The immutable v1 root may be verified read-only as a historical compatibility check, but no v1 trajectory or decision may enter the v2 pool.

Alternative considered: retain the unlaunched v1 slots or combine structurally valid v1 trajectories with v2. Rejected because the v1 global stop permanently invalidated continuation and all-slot attribution under that registration.

### 3. Treat launch qualification as a pre-lock operational gate

Qualification happens before `start` creates a run lock or ledger:

1. Replay the preserved failed qualification record and its eight bound predecessor files, require the original qualification root to remain byte-for-byte unchanged, and require the registered study root plus replacement qualification root to remain absent.
2. Re-render the canonical registration and require byte-for-byte equality.
3. Run the existing `dry-run` and verify all 24 commands, configs, IDs, seeds, v2 handshake paths, rates, budgets, and forbidden flags.
4. Run one bounded no-action CommunicationMod smoke in the active replacement qualification root using the registered Python/main/arguments and registration-bound handshake implementation. Before ready, poll only condition files and process state. Any transient live-log sharing violation is retried rather than interpreted as child failure. The child must receive state, publish ready, consume release, and be stopped before exploration callbacks, agent creation, or gameplay.
5. Treat the Java properties timestamp rewrite as raw-byte churn only: require the approved CommunicationMod semantic hash throughout the smoke, preserve the observed runtime bytes, and restore the verified pre-study baseline byte-for-byte afterward.
6. Require no study ledger, exploration manifest, trace, AI marker growth, run mutation, checkpoint mutation, global-log mutation, persistent CommunicationMod drift, or surviving process.
7. Exclusively write a deterministic self-hashed qualification record under the active replacement qualification root. Bind the failed qualification record, registration hash, source commit, registration-bound implementation hashes, command and Python path, pre-smoke CommunicationMod baseline, separately approved study-launch CommunicationMod semantics, checkpoint snapshot, dry-run digest, handshake record hashes, and isolation result.
8. Obtain independent review and exclusively publish a self-hashed reviewer attestation bound to the replacement qualification-record hash. Write no tracked artifact between qualification and `start`; immediately before launch replay both qualification identities and require the current HEAD plus every recorded static and operational binding to equal the reviewed candidate, then apply and verify only the pre-approved study-launch CommunicationMod semantics.

Both smoke attempts are operational evidence, not registered slots or outcome samples. The failed root is immutable immediately; the successful replacement record remains immutable during the run-lock window and both are incorporated into the repository closeout only after independent study verification. Neither weakens the real per-slot preclaim handshake, which remains the authority for slot launch.

Alternative considered: add another registration schema, release acknowledgment, or generic qualification subcommand before collection. Rejected because the failure occurred in an external monitor before protocol completion, no runtime implementation defect was observed, and every registered slot already performs the real-child handshake. Expanding tracked runtime semantics would create more source risk than a reviewed replacement qualification removes.

### 4. Freeze tracked source from run-lock creation through closeout

The candidate commit is final before qualification. After qualification, and without any intervening tracked write or commit, `start` creates the run lock and ledger exactly once from that tracked-clean source. From that point through finalization and standalone verification, no tracked file, registration byte, CommunicationMod semantic value, checkpoint, rate, threshold, or command may change.

Each `run-next` launches only the next registered slot. After each terminal slot, only the blinded structural monitor may be generated and inspected. A reboot, process exit, or apparent stall uses the registered recovery path plus the minimum screenshot/log evidence needed for safety; it never authorizes a retry or replacement.

Any global stop immediately prevents later launches. The registration is not repaired or resumed even if the operational problem is later understood.

### 5. Finalize once and keep authority closed

If all 24 slots are terminal without a global stop, `finalize` creates the complete registered pool and existing target/readiness/estimate/comparison artifacts once. If a global stop exists, `finalize` creates only the blocked claim and closeout. The standalone verifier must independently select and replay the applicable branch.

After the run-lock window closes, the repository may record the closeout, update deferred task checkboxes, rerun verification, and archive the change. `outcome_evidence_expansion_ready=true` authorizes only a later separately approved analysis or training proposal; it does not itself authorize RL, reward changes, gameplay-policy edits, causal claims, or promotion.

## Risks / Trade-offs

- [One full interrupted slot leaves at most the 575-trajectory minimum, while two may make readiness impossible] -> Preserve the fixed non-replacement schedule and report the observed shortfall; do not add games.
- [A no-action smoke proves one startup, not 24-slot reliability] -> Keep the real preclaim handshake on every slot and stop fail-closed on the first integrity failure.
- [The approximately 24-hour collection window is vulnerable to reboot or process interruption] -> Verify no stale process, disable avoidable restart/sleep conditions, monitor only structural health, and rely on deterministic recovery without replacement.
- [A defect may appear only during finalization] -> Preserve the frozen root, issue a blocked closeout if required, and repair tooling only in a later change; never regenerate evidence under edited source.
- [Qualification must remain durable without changing the qualified HEAD] -> Publish a self-hashed record and bound reviewer attestation exclusively under the separate qualification root, replay both before `start`, and copy their hashes into the repository only after the run-lock window closes.
- [Windows may transiently deny live log reads while the child opens or rotates its handler] -> Poll handshake files and process state before ready, retry sharing violations with bounded condition-based waits, and inspect the final log only after the child is stopped.
- [CommunicationMod rewrites Java properties with a timestamp] -> Bind semantic properties during execution, preserve observed runtime bytes, and require byte-for-byte restoration of the pre-study baseline before exit.
- [Pre-start validation can fail after applying the study CommunicationMod command] -> Preserve the baseline bytes, restore and recheck them on every failure before study-artifact publication, and treat any published registered study artifact as the irreversible boundary.

## Migration Plan

1. Keep the archived v1 change and external v1 root immutable; replay its blocked verifier as a compatibility baseline.
2. Generate the fixed v2 registration and review artifact, add exact-byte regressions if needed, and run focused/full offline verification.
3. Preserve and replay the first failed qualification root, record its clean isolation and no-retry verdict, then commit this explicitly reviewed replacement-root amendment without changing canonical registration or runtime implementation bytes.
4. From the amended tracked-clean candidate, run the full dry-run and bounded no-action qualification in the new replacement root, publish its external hashes and isolation result, and obtain independent review without changing tracked source.
5. Replay the failed root, successful replacement qualification record, and reviewer attestation; require the exact qualified HEAD and all static bindings; apply the pre-approved study-launch CommunicationMod semantics; verify every live binding; then create the run lock and ledger without an intervening commit. Restore the baseline on any failure before run-lock publication.
6. Execute slots 01-24 in order with blinded structural monitoring and no tracked edits; stop permanently on a global integrity condition.
7. Finalize exactly once, run the standalone verifier, restore and compare live isolation state, then record the deterministic closeout.
8. After the lock window closes, run focused and full Windows pytest, strict OpenSpec validation, byte/whitespace checks, independent review, and archive the change.

Before `start`, rollback means preserving every qualification identity and restoring the pre-study CommunicationMod baseline. When a pre-lock external procedure fails without implementation drift or registered study artifacts, the unchanged registration may proceed only after an explicit reviewed replacement-root amendment and complete fresh qualification; an implementation defect still requires a separate regression-backed change and fresh registration review. If `start` returns without publishing a run lock, ledger, child, or study artifact, prove that absence, restore the baseline, and require fresh qualification before another attempt. Once any registered study artifact exists, rollback means following the registered blocked or recovery path, independently verifying the frozen root, and only then restoring CommunicationMod configuration, even if slot one never launches.

## Open Questions

None. The study identity, schedule, rates, thresholds, target, estimator, active replacement qualification root, preserved failed qualification identity, stop behavior, and authority limits are fixed by this reviewed amendment before re-qualification.
