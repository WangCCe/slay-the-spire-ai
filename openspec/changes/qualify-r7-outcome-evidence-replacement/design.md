## Context

The v2 outcome-evidence study remains blocked before its run lock. R1-r3 are immutable failures, r4 is obsolete, and r5-r6 are retired static-only roots that ended before active-request publication. The tracked qualifier, broad request-bound isolation, and pre-request qualification observability repairs are implemented and archived, but no replacement identity exists and historical evidence authorizes neither retry nor `start`.

This amendment is the narrow bridge from those source repairs to one new qualification result. It must operate on Windows production Python, through the real CommunicationMod path, without allowing qualification mechanics to become gameplay or study execution. The proposal and offline artifacts themselves do not authorize a game launch.

## Goals / Non-Goals

**Goals:**

- Prepare one previously absent r7 request-v3/bootstrap-v1 candidate from a frozen clean source and exact live baseline.
- Require a reviewable, deterministic offline go/no-go boundary before any external root or CommunicationMod mutation.
- Permit at most one live no-action qualification after every offline gate passes.
- Independently replay and attest either a valid terminal or the exact partial/invalid/failed boundary, restore baseline isolation, and close r7 without retry.
- Produce a deterministic closeout that can inform a later study `start` review while granting no current authority.

**Non-Goals:**

- Editing qualifier, verifier, handshake, gameplay, policy, estimator, reward, or training source in this change.
- Invoking study `start`, creating a run lock or ledger, executing slots, inspecting outcomes, computing OPE, training, or promoting a policy.
- Repairing or retrying r1-r7, increasing timeouts as a substitute for evidence, or automatically preparing r8.
- Treating a clean local terminal as proof of broad live isolation without independent attestation.

## Decisions

### 1. Use one amendment with two irreversible gates

The change has an offline preparation/review gate followed by an optional at-most-once live gate. The external r7 root remains absent until the candidate, rollback material, direct-child R, and independent source-only review are complete. This keeps preparation reviewable without prematurely consuming the live identity.

Alternative considered: use separate preparation and live changes. Rejected because the live invocation would then depend on mutable cross-change anchors and duplicated rollback authority. The single amendment still requires a recorded go/no-go checkpoint before live execution.

### 2. Forbid source repair inside the identity amendment

The frozen qualifier/verifier implementation is an input, not an edit target. Any defect discovered before publication stops r7, preserves the rejected preparation with the external root absent, and moves to a separate TDD source-fix change. A defect discovered after publication stops any planned invocation, preserves and retires the published root under the supported no-invocation or live-boundary branch, and still moves to a separate source-fix change. After any observed or uncertain live boundary, r7 is retired regardless of whether a source fix later exists.

Alternative considered: fix small defects and regenerate r7 in place. Rejected because it collapses review commit, implementation binding, identity absence, and one-shot evidence into one mutable procedure.

### 3. Freeze S and one inert direct-child R

S identifies the exact clean source and existing canonical study registration. R is its direct child and contains only request-declared inert preparation and prelaunch-review paths. Qualification runs only with `HEAD == R`; every executable/importable path must match R, and the exact S-to-R diff must equal the request allowlist. Independent review transcripts and the go/no-go record produced after R remain outside the guarded repository worktree with external path, size, and SHA-256 anchors. Any closeout is first rendered externally only after the one-shot live boundary has ended and no further qualification launch is possible; repository import follows the branch-specific freeze in decision 7.

Alternative considered: launch from an uncommitted or later branch state. Rejected because current-worktree review cannot provide stable external anchors or source-only replay.

### 4. Keep candidate construction repository-local until go/no-go

Request, static-root image, launcher vector, expected inventory, and rollback bytes are first rendered into a guarded repository-local review area. Publishing the external static root and exact CommunicationMod launch configuration is a single post-review transition. A candidate rejected before that transition remains obsolete evidence. Once the root is published, any failed post-publication comparison retires r7 even when no invocation occurred; the root remains immutable and is never deleted or rewritten into another r7.

Alternative considered: build directly in the game directory and review in place. Rejected because review failure would leave ambiguous live state before launch authority exists.

### 5. Bind the live invocation to exact before/after isolation

Immediately before invocation, the operator rechecks the exact CommunicationMod bytes, marker/run/checkpoint/global-log inventories, static root, source anchors, and zero target processes against the reviewed go record. The invocation uses `D:\anaconda\envs\stsai\python.exe`, the fixed stdlib launcher token, and the request-bound initialization timeout. The qualifier owns the no-action child handshake; no external release monitor or second launch exists.

If the qualifier has not reached its request-owned restoration boundary, controlled cleanup stops Java/owned processes, restores the exact prelaunch bytes, and independently recollects isolation. Evidence is preserved in every branch.

### 6. Separate producer terminal evidence from external attestation

A producer terminal is necessary but insufficient. The standalone verifier receives external S/R/request/result anchors and replays v3 without producer builders; a separate attestation binds the verifier output to CommunicationMod restoration, protected inventories, and process death observed outside the qualifier. Only the conjunction may classify r7 as qualified.

Alternative considered: accept the local completion record as the qualification result. Rejected because r3-r6 demonstrated that process ownership and broad isolation facts can diverge from internal lifecycle evidence.

### 7. Classify publication separately and preserve the qualified R freeze

The operational result has four governance dispositions: `obsolete_before_publication`, `retired_after_publication_without_invocation`, `retired_after_live_boundary`, or `qualified_for_start_review`. The obsolete disposition requires the external root and live configuration to remain unchanged. The post-publication/no-invocation disposition preserves the exact static root, restores the exact CommunicationMod baseline, binds evidence that the operator invocation command was not issued, target-process inventory stayed zero, and control/result paths stayed absent, and permanently forbids reuse without claiming a live protocol boundary. Any target process, control path, launch evidence, or uncertainty after publication uses the live-boundary disposition instead. Obsolete and retired branches have no usable start handoff, so their repository closeout, task updates, sync, and archive may occur immediately after evidence review.

The qualified branch is different: the existing study design requires `start` from tracked-clean R without an intervening tracked write or commit. Its attestation, handoff, and provisional closeout therefore remain outside the repository with exact external anchors; HEAD and the worktree stay at R, this change remains active, and no checkbox is updated. If the later reviewed start decision declines launch, the freeze may be explicitly released and the closeout imported. If `start` creates the run lock, import is deferred until the study's tracked-write prohibition ends after finalization and independent verification. This amendment never invokes `start` itself.

Alternative considered: commit the qualified closeout before handing off to the study. Rejected because that descendant commit would make r7 unusable under the already frozen exact S/R launch contract.

## Risks / Trade-offs

- [The game or CommunicationMod can terminate before a claim appears] -> Preserve external launch evidence, restore and attest the baseline, conservatively retire r7, and do not infer the missing internal stage.
- [Review artifacts can drift between go/no-go and launch] -> Rehash every bound byte and recheck `HEAD == R`, exact static inventory, configuration, and process state immediately before invocation; any drift stops before launch.
- [Publication can succeed before its final comparison fails] -> Do not issue the invocation; preserve the published static root, restore and attest the exact baseline, and retire r7 without deleting or reusing it. Claim no invocation only when zero target processes and absent control paths remain provable; otherwise classify an uncertain live boundary.
- [A terminal can look successful while broad isolation is uncertain] -> Require independent attestation over restored bytes, protected inventories, and zero processes; uncertainty retires r7.
- [The one-shot rule can consume another identity without qualifying the study] -> Accept fail-closed retirement as a valid amendment closeout and forbid automatic r8; the alternative would weaken immutable evidence.
- [Full regression evidence is expensive] -> Reuse only transcript evidence whose exact source inputs still match S; otherwise rerun the scoped focused and complete suites serially before go/no-go.
- [The OpenSpec change can remain active after a qualified result] -> Keep the qualified evidence and provisional closeout externally anchored, leave repository state frozen at R, and import/archive only after the existing study contract releases tracked writes.

## Migration Plan

1. Approve and commit this amendment without creating r7 or changing live configuration.
2. Freeze S; prove the identity/root absent; capture exact live baseline and protected inventories; render repository-local candidate bytes and regression evidence.
3. Review the proposed inert S-to-R tree, resolve documentation findings, create and push one final direct-child R, then independently replay and re-review every exact post-commit anchor before recording the external offline go/no-go decision.
4. On no-go, preserve obsolete preparation, leave the external root absent, write closeout, and stop. On go, publish the exact static root and reviewed CommunicationMod configuration. If the final post-publication comparison fails before operator invocation, restore the baseline, preserve and retire the root, attest no invocation only from zero-process/control-path evidence, otherwise bind an uncertain live boundary, and stop.
5. Only after the post-publication comparison passes, recheck all invocation anchors and invoke r7 once through real CommunicationMod. Preserve the resulting root and external observations.
6. Independently verify, restore/recollect isolation as required, attest the exact branch, and render the deterministic closeout externally first.
7. For obsolete or retired branches, import and commit the closeout and evidence-backed status updates immediately. For a qualified branch, preserve tracked-clean R and hand the external package to the later `start` review; import, sync, and archive only after that decision declines launch or the full run-lock tracked-write window closes. Do not invoke `start` or prepare another identity in this amendment.

Rollback is source-neutral. Before publication, restore no live state because the game directory remains unchanged. After publication but before operator invocation, never delete the r7 root; restore exact request-bound CommunicationMod bytes, independently verify protected inventories, and retire r7. A no-invocation claim additionally requires zero target processes and absent control paths; any uncertainty follows the live-boundary cleanup and retirement path. After invocation, preserve the root, stop controlled processes, restore the baseline, verify protected inventories and process death, and retain all evidence for review. A qualified branch also preserves R and the clean worktree until the later frozen-study boundary permits tracked changes.

## Open Questions

No design question remains before proposal approval. Exact S/R commits, hashes, paths, byte sizes, baseline inventories, and the go/no-go result are generated and frozen during implementation rather than guessed in planning.
