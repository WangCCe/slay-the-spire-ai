## Context

The immutable 2026-07-15 v1 study stopped fail-closed after slot 14 and now passes the independent blocked-closeout verifier. The recovery change added registration-v2 generation, an attempt/ready/release handshake with the real CommunicationMod child, v1 launch refusal, and independent normal/blocked verification. It deliberately created no new registration and authorized no collection.

The unresolved question is still evidence sufficiency. The frozen B3-B7 pool has only one victory and zero deterministic-Current weight on that victory, while the blocked v1 study cannot contribute a selectively recovered pool. The repository therefore needs one fresh, immutable study instance that uses the already reviewed v2 implementation without changing the behavior policy, target, estimator, thresholds, or authority boundary.

The candidate study identity is fixed as:

- Study ID: `noncombat-outcome-evidence-expansion-20260716-v2`
- Registration: `reports/noncombat_outcome_evidence_expansion_20260716_v2_registration.json`
- Artifact root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2`
- Prepared obsolete qualification root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r4` (static config only; never launched or consumed)
- Preserved r3 failure root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r3`
- r3 failure-record self-hash: `e495ce302f0ddf9628962e0d4147614a0cf9b9c7c010f256662a98eae76b033d`
- r3 failure-record file SHA-256: `5a3c47f5b93d7c1f66b5de6c32d3af139188b60735fa36733c6b3c6ee772cfec`
- r3 final root inventory SHA-256: `2a63cf3b7505ebf6d9e2f605eade7deec3c0afdaaa4da90ca6a99b517c82cb16`
- Preserved r2 failure root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r2`
- r2 failure-record self-hash: `8bb9b396e129e017fd84fb4aabe7fa6d02bb51b0c7c147836dbf29e7c289c95c`
- r2 failure-record file SHA-256: `3fbace492dd0f849bdf86deff1df97dfc4ae3b77a427545413ac48170c9c2540`
- Preserved r1 failure root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification`
- r1 failure-record self-hash: `ccd76824c90a9726c57b48a7f71d8bc1d8da94df6c686ae36eff10a1b72db41f`
- r1 failure-record file SHA-256: `0677212e139270219be597e26f9e79bab30ab2c74fc5c810c41360c2d7dd545a`
- Superseded registration hash: `86cb17077fe5dc7123307660eef4c1986dc11f48837308fed714faf88c73f22a`
- Superseded registration file SHA-256: `2a7e937da2c63d6c235452349d3f66de5870525d578c51deccbb87a522baef6a`
- Reviewed handshake-fix commit: `79cf98f89`
- Obsolete prep-only source snapshot: `76ed7135ad2e8236c77b20957a0617262c9e77b6`
- Obsolete prep-only request self-hash: `f21313b80fedfccdea76c0e69d3d3d44f06289ba033159537d73f0202f3c039e`
- Obsolete prep-only request file SHA-256: `1e04b2a378e434c16f45cdb8a389dd527d2419ae6625d6a141e1a9fb0be4792c`
- Obsolete prep-only request size: `5996`
- Active qualification root/source/request: none until the isolation repair is committed and a later reviewed amendment binds a previously absent replacement root
- Seed base: `2026071600`

The registered study root remains absent. The r4 root was created only with its canonical static config; the obsolete request was never committed as R or copied into the root, and no active request, attempt, child, handshake, or terminal exists. Independent review found that its v1 request/result contract did not machine-bind broad isolation, so r4 is permanently non-launchable and non-authorizing. The r1, r2, and r3 qualification roots remain immutable failures: r1 stopped on an external log-sharing failure, r2 exposed the old 30-second cold-start implementation defect, and r3 preserved valid attempt/ready evidence but no release. Any replacement must follow the isolation repair with a fresh source snapshot, regenerated registration bindings, a v2 request, a direct-child review commit, and a previously absent root.

## Goals / Non-Goals

**Goals:**

- Regenerate and independently review one canonical registration-v2 artifact under the fixed 120-second handshake, with 24 ordered 25-game slots and the unchanged evidence root.
- Qualify the exact candidate registration and registration-bound implementation before creating the run lock.
- Execute collection blindly with the existing launch-at-most-once handshake, fixed schedule, fixed behavior distribution, and no tracked source edits.
- Produce exactly one independently verified normal or blocked closeout and preserve all source evidence.
- Decide only whether the registered evidence is ready, inconclusive, or blocked.

**Non-Goals:**

- Do not reuse, resume, repair, extend, pool, or rewrite any v1 study artifact.
- Do not change gameplay policy, exploration rates, executable alternatives, target policy, OPE estimator, bootstrap, evidence thresholds, or promotion gates.
- Do not train, tune, redesign rewards or RL spaces, execute Bottled actions live, or authorize policy promotion.
- Do not fix another implementation defect inside the frozen study. The r2 defect was fixed separately; any later defect requires another regression-backed change, regenerated registration, and newly reviewed qualification identity.

## Decisions

### 1. Freeze the reviewed post-fix implementation and regenerate registration

The change will use the post-fix registration builder, dry-run, run-lock, ledger, handshake, monitor, finalizer, and standalone verifier containing `79cf98f89`. Implementation files are read-only inputs to this study amendment. Registration generation tests assert exact bytes, but no additional gameplay or analysis implementation change is planned.

If registration replay, dry-run, the no-action smoke, focused tests, full tests, or independent review exposes a defect, the study will not start. The defect will be handled in a separate OpenSpec change with a red regression; this change can be revised only after that fix and a fresh registration review.

The r2 qualification exposed such a defect: CommunicationMod received protocol `ready`, but its first callback-free state arrived after the registered 30-second readiness deadline. `fix-cold-start-study-handshake-timeout` reproduced the defect at 45 simulated seconds, changed the fixed launchable contract to 120 seconds, added exact/late deadline rejection, passed focused and full tests, and committed the fix separately as `79cf98f89`.

The old 30-second registration is therefore superseded pre-lock evidence and cannot be launched. The post-orchestrator task 7.1 replay re-rendered the then-current 120-second registration byte-for-byte and retained canonical hash `7df8036e111fb55ece15154796d494ea857a74984c9d1a224c2b61f8fc710ace`, file SHA-256 `a0e282699ede7d1ea38b2d81f029ce5e823b924d81c5ca7cdbc9a45ddc2eb6c2`, and size 19796. The historical r3-era review and obsolete r4 preparation remain immutable context only. Because `bind-qualification-isolation-evidence` changes registration-bound implementation bytes and qualification schemas, a later amendment must canonically re-render the registration and bind the new source snapshot before any replacement request is reviewed.

Alternative considered: retain the old registration and override only the r3 timeout. Rejected because qualification would then test a different contract from the registered study and its implementation hashes.

### 2. Freeze one new study identity and preserve the v1 boundary

The regenerated v2 registration will use the fixed identity above, schema v2, the Windows production Python, the existing 24-by-25 schedule, `card_reward=300` basis points, `shop=1000` basis points, two alternative attempts per run, deterministic Current, the existing thresholds and estimator calibration, readiness 120, and release 10. Slot IDs and seeds derive only from the fixed study ID and seed base.

The replacement qualification, run lock, ledger, configs, traces, manifests, pool, estimates, and closeout will reference only a final v2 candidate regenerated after the isolation repair. The three preserved failed qualification roots and prepared r4 root are pre-lock operational history and can never enter the v2 pool or satisfy a launch gate. The immutable v1 study root may be verified read-only as a historical compatibility check, but no v1 trajectory or decision may enter the v2 pool.

Alternative considered: retain the unlaunched v1 slots or combine structurally valid v1 trajectories with v2. Rejected because the v1 global stop permanently invalidated continuation and all-slot attribution under that registration.

### 3. Treat launch qualification as a pre-lock operational gate

Qualification happens before `start` creates a run lock or ledger:

1. Preserve and replay r1, r2, and r3 from their immutable roots, and preserve the prepared r4 config plus obsolete request anchors as non-authorizing history. Require the registered study root to remain absent.
2. Complete `bind-qualification-isolation-evidence` offline and commit it as a fresh source snapshot S. Re-render the canonical registration against S and review every changed implementation binding.
3. In a later tracked amendment, name a previously absent replacement qualification root, build a request-v2 baseline that binds CommunicationMod bytes, marker state, run/checkpoint inventories, and global logs, and commit only the declared inert allowlist as direct-child R.
4. From tracked-clean `HEAD == R`, point CommunicationMod only at the fixed stdlib `python -I -S -c` trusted launcher and invoke `qualify` with externally preserved S/R/request anchors. The bootstrap must prove the exact chain and unchanged registration/implementation bytes before publishing an active request or starting a child.
5. Let the tracked qualifier own request publication, the single child, attempt/ready/release, exact CommunicationMod restoration, terminal isolation recollection, child-death proof, and exclusive completion/failure sealing. No external monitor may own or race the protocol.
6. Preserve terminal self-hash, file SHA-256, and size externally, then run the independent verifier with exact S/R/request/terminal anchors. The verifier must independently recollect the restored resources and reject any drift, schema mismatch, or live/ambiguous child PID.
7. A passing v2 completion and independent attestation authorize only a later `start` decision after exact replay. Any failure or partial prefix makes the replacement root immutable, forbids retry and start, and requires another explicit amendment.

All qualification attempts are operational evidence, not registered slots or outcome samples. The r1/r2/r3 roots are immutable failures, while r4 is an unconsumed preparation that can never become active. A future replacement terminal remains immutable during any run-lock window. None weakens the real per-slot preclaim handshake, which remains the authority for slot launch.

Alternative considered: launch the already prepared r4 request and rely on external snapshots. Rejected because the request/result/verifier chain cannot independently prove broad isolation. External operator observations may supplement diagnostics but cannot substitute for request-bound, terminal-bound, independently recollected evidence.

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
- [Qualification must remain durable without changing the qualified HEAD] -> Commit only a freshly regenerated inert direct-child R allowlist, publish a self-hashed replacement terminal exclusively under its new qualification root, pin its external anchors, and replay it plus all historical identities before `start`.
- [Windows may transiently deny live log reads while the child opens or rotates its handler] -> Do not read live logs in the qualification protocol. The owner-controlled qualifier uses only canonical control files, inherited process state, and bounded source/isolation checks; inspect logs only after the child is stopped.
- [CommunicationMod rewrites Java properties with a timestamp] -> Bind semantic properties during execution, preserve observed runtime bytes, and require byte-for-byte restoration of the pre-study baseline before exit.
- [Pre-start validation can fail after applying the study CommunicationMod command] -> Preserve the baseline bytes, restore and recheck them on every failure before study-artifact publication, and treat any published registered study artifact as the irreversible boundary.

## Migration Plan

1. Keep the archived v1 change and external v1 root immutable; replay its blocked verifier as a compatibility baseline.
2. Generate the fixed v2 registration and review artifact, add exact-byte regressions if needed, and run focused/full offline verification.
3. Preserve and replay r1/r2/r3 and preserve the r4 config/request preparation as obsolete, unconsumed, and non-authorizing.
4. Complete and commit the request-bound isolation repair as fresh S, then in a separate reviewed amendment re-render the registration, name a previously absent replacement root, create request v2, and commit exactly the declared inert paths as direct-child R.
5. From tracked-clean `HEAD == R`, pin the full R and request anchors externally, run the 24-launch dry-run, invoke the tracked qualifier exactly once through real CommunicationMod, and independently replay its terminal without changing tracked source.
6. Replay all historical roots plus the successful replacement terminal and independent attestation; require the exact qualified HEAD and all static/live bindings; only then create the run lock and ledger without an intervening commit.
7. Execute slots 01-24 in order with blinded structural monitoring and no tracked edits; stop permanently on a global integrity condition.
8. Finalize exactly once, run the standalone verifier, restore and compare live isolation state, then record the deterministic closeout.
9. After the lock window closes, run focused and full Windows pytest, strict OpenSpec validation, byte/whitespace checks, independent review, and archive the change.

Before `start`, rollback means preserving every qualification identity, request/terminal prefix, and superseded registration byte, then restoring the pre-study CommunicationMod baseline. A pre-lock operational failure still requires an explicit reviewed replacement-root amendment and complete fresh qualification; an implementation defect additionally requires a separate regression-backed change and binding refresh. If `start` returns without publishing a run lock, ledger, child, or study artifact, prove that absence, restore the baseline, and require fresh qualification before another attempt. Once any registered study artifact exists, rollback means following the registered blocked or recovery path, independently verifying the frozen root, and only then restoring CommunicationMod configuration, even if slot one never launches.

## Open Questions

The study identity, schedule, rates, thresholds, target, estimator, three preserved failed qualification identities, 120/10 handshake bounds, stop behavior, and authority limits remain fixed. The active replacement qualification root and new S/direct-child-R/request-v2 anchors are intentionally unset until the isolation repair lands and a later amendment reviews them.
