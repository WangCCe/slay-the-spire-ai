## Context

The immutable 2026-07-15 v1 study stopped fail-closed after slot 14 and now passes the independent blocked-closeout verifier. The recovery change added registration-v2 generation, an attempt/ready/release handshake with the real CommunicationMod child, v1 launch refusal, and independent normal/blocked verification. It deliberately created no new registration and authorized no collection.

The unresolved question is still evidence sufficiency. The frozen B3-B7 pool has only one victory and zero deterministic-Current weight on that victory, while the blocked v1 study cannot contribute a selectively recovered pool. The repository therefore needs one fresh, immutable study instance that uses the already reviewed v2 implementation without changing the behavior policy, target, estimator, thresholds, or authority boundary.

The candidate study identity is fixed as:

- Study ID: `noncombat-outcome-evidence-expansion-20260716-v2`
- Registration: `reports/noncombat_outcome_evidence_expansion_20260716_v2_registration.json`
- Artifact root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2`
- Qualification root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification`
- Seed base: `2026071600`

Both external roots must be absent before their respective procedures begin. If either identity collides with existing bytes, this change stops for review rather than silently choosing a different path or seed.

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

Alternative considered: repair small defects inline and retain the same candidate registration. Rejected because the registration and qualification evidence would no longer describe the source that generated them.

### 2. Freeze one new study identity and preserve the v1 boundary

The v2 registration will use the fixed identity above, schema v2, the Windows production Python, the existing 24-by-25 schedule, `card_reward=300` basis points, `shop=1000` basis points, two alternative attempts per run, deterministic Current, and the existing thresholds and estimator calibration. Slot IDs and seeds derive only from the fixed study ID and seed base.

The registration, qualification, run lock, ledger, configs, traces, manifests, pool, estimates, and closeout will reference only the v2 root. The immutable v1 root may be verified read-only as a historical compatibility check, but no v1 trajectory or decision may enter the v2 pool.

Alternative considered: retain the unlaunched v1 slots or combine structurally valid v1 trajectories with v2. Rejected because the v1 global stop permanently invalidated continuation and all-slot attribution under that registration.

### 3. Treat launch qualification as a pre-lock operational gate

Qualification happens before `start` creates a run lock or ledger:

1. Re-render the canonical registration and require byte-for-byte equality.
2. Run the existing `dry-run` and verify all 24 commands, configs, IDs, seeds, v2 handshake paths, rates, budgets, and forbidden flags.
3. Run one bounded no-action CommunicationMod smoke in the separate qualification root using the registered Python/main/arguments and the registration-bound handshake implementation. The child must receive state, publish ready, consume release, and be stopped before exploration callbacks, agent creation, or gameplay.
4. Require no study ledger, exploration manifest, trace, AI marker growth, checkpoint mutation, persistent CommunicationMod drift, or surviving process.
5. Exclusively write a deterministic self-hashed qualification record under the external qualification root. Bind the registration hash, source commit, registration-bound implementation hashes, command and Python path, pre-smoke CommunicationMod baseline, separately approved study-launch CommunicationMod semantics, checkpoint snapshot, dry-run digest, handshake record hashes, and isolation result.
6. Obtain independent review and exclusively publish a self-hashed reviewer attestation bound to the qualification-record hash. Write no tracked artifact between qualification and `start`; immediately before launch replay the record and attestation bytes and require the current HEAD plus every recorded static and operational binding to equal the reviewed candidate, then apply and verify only the pre-approved study-launch CommunicationMod semantics.

The smoke is operational evidence, not a registered slot or outcome sample. Its external record remains immutable during the run-lock window and is incorporated into the repository closeout only after independent study verification. It does not weaken the real per-slot preclaim handshake, which remains the authority for slot launch.

Alternative considered: add another registration schema, release acknowledgment, or generic qualification subcommand before collection. Rejected for this study because the reviewed v2 protocol already passed a real no-action smoke and every slot performs the real-child handshake; expanding runtime semantics would create more source risk than the bounded qualification removes.

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
- [Pre-start validation can fail after applying the study CommunicationMod command] -> Preserve the baseline bytes, restore and recheck them on every failure before study-artifact publication, and treat any published registered study artifact as the irreversible boundary.

## Migration Plan

1. Keep the archived v1 change and external v1 root immutable; replay its blocked verifier as a compatibility baseline.
2. Generate the fixed v2 registration and review artifact, add exact-byte regressions if needed, and run focused/full offline verification.
3. Commit the candidate registration, run the full dry-run and bounded no-action qualification, publish its external hashes and isolation result, and obtain independent review without changing tracked source.
4. Replay the external qualification record and reviewer attestation, require the exact qualified HEAD and all static bindings, apply the pre-approved study-launch CommunicationMod semantics, verify every live binding, then create the run lock and ledger without an intervening commit. Restore the baseline on any failure before run-lock publication.
5. Execute slots 01-24 in order with blinded structural monitoring and no tracked edits; stop permanently on a global integrity condition.
6. Finalize exactly once, run the standalone verifier, restore and compare live isolation state, then record the deterministic closeout.
7. After the lock window closes, run focused and full Windows pytest, strict OpenSpec validation, byte/whitespace checks, independent review, and archive the change.

Before `start`, rollback means abandoning the unlaunched registration candidate, preserving the qualification record, and restoring the pre-study CommunicationMod baseline. If `start` returns without publishing a run lock, ledger, child, or study artifact, prove that absence, restore the baseline, and require fresh qualification before another attempt. Once any registered study artifact exists, rollback means following the registered blocked or recovery path, independently verifying the frozen root, and only then restoring CommunicationMod configuration, even if slot one never launches.

## Open Questions

None. The study identity, schedule, rates, thresholds, target, estimator, qualification boundary, stop behavior, and authority limits are fixed before implementation.
