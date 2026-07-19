# V2 R6 Tracked Qualification Review

Date: 2026-07-18

Status: offline candidate prepared for direct-child review commit; no r6 qualifier, game, active request, run lock, collection, OPE, or training process has started.

## Decision

R5 review commit `2936c547bd7917fdbbc487470326716129e3fbe2` passed the independent source-only verifier with 95 checks. One real r5 ModTheSpire invocation then exited before the qualifier published its active request. CommunicationMod applied its implicit 10-second external-process initialization timeout while the exact reviewed Git/isolation preflight required about 17 seconds. The r5 root still contains only its static config; no active request, attempt, ready, release, completion, failure, marker, run, checkpoint, global-log, registered study root, run lock, or ledger changed. The original 505-byte CommunicationMod configuration was restored exactly, the game was stopped, and r5 is retired without retry.

R6 uses no runtime, schema, registration, behavior, estimator, threshold, or policy change. Source snapshot S is the retired-r5 review commit `2936c547bd7917fdbbc487470326716129e3fbe2`. The previously absent r6 root contains exactly one canonical static config. Before request generation, the CommunicationMod baseline was changed from 505 to 535 bytes by inserting exactly `maxInitializationTimeout=120`; every other original byte and semantic property remains fixed. The original 505-byte value remains preserved in the committed r5 request for final post-study restoration.

Canonical request v2 exists only as the inert repository review source named below. It has not been published to the active request path and no r6 process or protocol prefix exists. The request, this report, and the five OpenSpec files listed below must be committed together as review commit R. R is valid only if:

- `parent(R) == S`
- `HEAD == R` at launch
- R has exactly one parent
- the exact S-to-R path set equals the request's sorted seven-path allowlist
- every changed path is inert and non-executable
- registration and all 14 registered implementation files have identical bytes at S, R, and the launch worktree
- no untracked or ignored executable/importable path or reparse point exists in the launch worktree

R cannot be embedded in its own committed bytes. Its full 40-hex value must be resolved after commit and preserved externally with the request anchors. A missing, abbreviated, stale, or mismatched R keeps qualification blocked.

## Canonical Registration

| Field | Value |
|---|---|
| Path | `reports/noncombat_outcome_evidence_expansion_20260716_v2_registration.json` |
| Schema | `noncombat-outcome-evidence-registration-v2` |
| Canonical hash | `7df8036e111fb55ece15154796d494ea857a74984c9d1a224c2b61f8fc710ace` |
| File SHA-256 | `a0e282699ede7d1ea38b2d81f029ce5e823b924d81c5ca7cdbc9a45ddc2eb6c2` |
| Size | 19796 bytes |
| Schedule | 24 ordered slots x 25 attempts = 600 attempts |
| Behavior | `card_reward=300` bps, `shop=1000` bps, budget 2; event/route shadow-only |
| Handshake | readiness 120 seconds; release 10 seconds |
| Command authority | Windows production Python, `--eval`, no training flag |

A fresh dry-run at S produced 24 launch records, canonical LF SHA-256 `e108f56b4912a56f8dc0552a915d40d9ff4f882aab1ab1e0f1d91dd49452bdad`, and canonical size 57941 bytes. The digest differs from the pre-r5 value only because each inert slot config binds source snapshot S. It wrote no study artifact.

## Request Anchors

| Field | Value |
|---|---|
| Request source | `reports/noncombat_outcome_evidence_expansion_20260716_v2_r6_qualification_request.json` |
| Schema | `noncombat-outcome-evidence-qualification-request-v2` |
| Request self-hash | `fc5332ffca8b00a1e5132047d07538825369f187db030d9e080a91d37fa8496c` |
| Request file SHA-256 | `28c174d6fba875ba110b107c92da5d522664ead81d9bf5c0db71db6fc3748b69` |
| Request size | 8886 bytes |
| Isolation baseline hash | `a37a8e64fff42339b9d13bcede2dba5370d678c9e08b74d1e31107ccb4d7aed4` |
| Source snapshot S | `2936c547bd7917fdbbc487470326716129e3fbe2` |
| Review commit R | full 40-hex direct child containing this seven-path review; resolve and pin externally after commit |
| Qualification ID | `noncombat-outcome-evidence-expansion-20260716-v2-qualification-r6` |
| Qualification root | `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r6` |
| Static config SHA-256 | `b1b734e885ba7404e5492bb8911be97494eab789ddb21c0fb6230f46d3161404` |
| Static config size | 949 bytes |
| Marker boundary | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\ai_games.txt`, 15255 lines at request creation |

The complete pre-request r6 inventory is exactly `qualification-config.json`. The active request, attempt, ready, release, completion, failure, manifest, trace, registered study root, run lock, and ledger are absent.

The request review allowlist is exactly:

1. `openspec/changes/add-tracked-outcome-qualification-orchestrator/tasks.md`
2. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/design.md`
3. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/proposal.md`
4. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/specs/noncombat-outcome-evidence-expansion/spec.md`
5. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/tasks.md`
6. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r6_qualification_request.json`
7. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r6_qualification_review.md`

## CommunicationMod Baseline Transition

| Field | Preserved pre-r6 value | Request-bound r6 value |
|---|---|---|
| File SHA-256 | `374806e6386940a5945ffd03411b526d6a21c002b938bb4db253780f787b8e9a` | `a404525790c925423d6298b639322b370ccf37414f9808362bd24a8dc9feb202` |
| Size | 505 bytes | 535 bytes |
| `maxInitializationTimeout` | absent, so CommunicationMod uses default 10 | `120` |
| Other semantic properties | fixed baseline command, `runAtGameStart=true`, `verbose=false`, `waitForProcess=true` | identical |

The r6 launch configuration must retain `maxInitializationTimeout=120` and all other non-command properties while replacing only `command` with the exact trusted qualifier launcher. CommunicationMod may rewrite formatting and its timestamp while loading. The qualifier compares semantics before request publication and restores the exact 535-byte r6 baseline before terminal sealing. The independently recollected post-terminal observation must equal that baseline. The 505-byte pre-r6 value is not the r6 terminal baseline; it is preserved for final restoration only after the qualified study's integrity window closes.

## Isolation Baseline

| Resource | Bound observation |
|---|---|
| CommunicationMod config | SHA-256 `a404525790c925423d6298b639322b370ccf37414f9808362bd24a8dc9feb202`; 535 bytes; exact raw bytes plus five semantic properties including initialization timeout 120 |
| AI marker | SHA-256 `88db1899d2b442c90380f74aefcf10eab21cc9e91c917295d8c0f3d02da67a76`; 183060 bytes; 15255 lines |
| Recursive runs inventory | SHA-256 `778598b31c5097f4622a7db7ac09ff99e954ed3354b7a40d81b6328f9d713a0a`; 1365 entries; 5810995 bytes |
| Registered checkpoint inventory | SHA-256 `f1549213f99463d62be3a870fe61500d800c09357dc77fbebb647660aac146b2`; 208 entries; 1356047034 bytes; patterns `rl_combat_model_*.pth`, `rl_model_*.pth` |
| `ai_debug.log` | SHA-256 `f1865917572af46d0ff25f0f0dd73ba2c124f6b3fbcc89935f2493efc96e8847`; 3382856 bytes |
| `communication_mod_errors.log` | SHA-256 `bd8b833a075488d834f9af33075d48c56258801a07e3e9a41714e023901b7197`; 1167005 bytes |

The request baseline is a pre-launch observation, not evidence that these resources will remain equal. The tracked qualifier must replay the baseline before publication, bind post-exit observations and exact CommunicationMod restoration into its terminal, and prove the child PID is dead. The independent verifier must recollect the resources and PID rather than trusting terminal assertions.

## Implementation Binding

| Registered path | SHA-256 at S | Bytes |
|---|---|---:|
| `analysis_scripts/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| `analysis_scripts/noncombat_exploration_evidence.py` | `ba6e46c2c8418e9d47f059c02d35e71a2d65165a27d5b3b68e43cb5c43d04016` | 44201 |
| `analysis_scripts/noncombat_ope_estimate_artifacts.py` | `2486b7589b221193059e615ff3a6c5aa4573cd5017e800adfec8f51e9a52b98e` | 17242 |
| `analysis_scripts/noncombat_ope_estimation.py` | `39e4b981348918ec8ab3e18c23f62f261be6a905d4b4c9826cfc3cae7e8bf370` | 36646 |
| `analysis_scripts/noncombat_ope_readiness.py` | `b62bd274c41a56ad3721c5390736c9d19171fe6037fd8edb278f848f3adf677d` | 58877 |
| `analysis_scripts/noncombat_outcome_evidence_expansion.py` | `f73708530251ff75b411eeb0ad8254b4782e2548fda257f530305b2de29d3256` | 125725 |
| `analysis_scripts/verify_noncombat_ope_artifacts.py` | `5e5e4eb2b7090fb89e57b2634dc4289bbcb4b7c81857d05d15fd22bfea927519` | 33629 |
| `analysis_scripts/verify_noncombat_ope_estimates.py` | `de0e85eca294725adc9553e7870528f69777f248a39630891e253c39a1e52991` | 52027 |
| `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py` | `ecd128f20e90a6c70ee83fe0aef067f7df1b74a1bcd9bcf8ecaf2391d4f99ac5` | 263315 |
| `main.py` | `0740f26b096e474172fa242a848cf856152c4188ce700a2fd63311aac5ce0fa4` | 58178 |
| `scripts/run_noncombat_outcome_evidence_expansion.py` | `25e8d6e7ae8ad155910d8033f9fa7c24aa9a928260f378d4f3748baa0329d669` | 268008 |
| `spirecomm/ai/noncombat_exploration.py` | `1a075b7fff8b46ab095af4d9a6bbf3dd4f2c7d12b7115d3004b64eeffded7dc5` | 82322 |
| `spirecomm/ai/noncombat_exploration_runtime.py` | `ff013f04b6e00cbf11bf7e378fa4d72146f578d65f9c01519f68d92f1bc03030` | 19344 |
| `spirecomm/communication/study_handshake.py` | `5d61573b4d5e590cffc94d015db88794a9582524d73f9bb1eb743eb78aa0ee0f` | 25473 |

## Preserved Historical Boundary

| Identity | Preserved anchor | Governing result |
|---|---|---|
| r1 | failure self-hash `ccd76824c90a9726c57b48a7f71d8bc1d8da94df6c686ae36eff10a1b72db41f` | immutable pre-ready failure; no retry/start |
| r2 | failure self-hash `8bb9b396e129e017fd84fb4aabe7fa6d02bb51b0c7c147836dbf29e7c289c95c` | immutable 30-second cold-state implementation failure; separately fixed; no retry/start |
| r3 | failure self-hash `e495ce302f0ddf9628962e0d4147614a0cf9b9c7c010f256662a98eae76b033d` | valid attempt/ready, absent release; immutable; no retry/start |
| r4 | request-v1 self-hash `f21313b80fedfccdea76c0e69d3d3d44f06289ba033159537d73f0202f3c039e` | static config and prep-only request source; never committed as R, published, launched, or consumed; permanently obsolete |
| r5 | request-v2 self-hash `b80b5311018c6c39de6df55c8e1d9090826e07bbd606711b4d0c4d68b4d1cfce`, review commit `2936c547bd7917fdbbc487470326716129e3fbe2` | source-only verifier passed; one real launch ended before active request publication under implicit timeout 10; static config only; retired without retry/start |

The r3 final root inventory remains `2a63cf3b7505ebf6d9e2f605eade7deec3c0afdaaa4da90ca6a99b517c82cb16`. None of r1-r5 may be retried, pooled, or used as qualification/start authority.

## Verification And Hygiene

The unchanged isolation implementation previously passed its 253-test qualification slice, the 3120-test full Windows suite, strict OpenSpec validation, compile checks, and independent code review. R6 changes no implementation or schema byte, so this amendment requires exact artifact replay, strict OpenSpec validation, source-only verifier replay, and live evidence rather than repeating the full source suite before R.

R5 cleanup proved:

- no active request, handshake, terminal, marker, run, checkpoint, global-log, study-root, run-lock, or ledger change
- exact restoration of CommunicationMod SHA-256 `374806e6386940a5945ffd03411b526d6a21c002b938bb4db253780f787b8e9a`, size 505
- exact equality of all r5 request-bound isolation resources after Java shutdown
- no surviving target Java or Python process

The diagnostic screenshot was moved intact outside the repository to `D:\PycharmProjects\slay-the-spire-ai-test-artifact-quarantine\20260718-r5-pre-request-timeout`. Source scanning at r6 S then returned exact commit `2936c547bd7917fdbbc487470326716129e3fbe2`. The deliberate 535-byte baseline transition and r6 request were generated with bytecode writes disabled.

## Launch And Terminal Gate

Before R, strict review must prove the request schema and anchors, exact one-parent-chain design, allowlist, registration/implementation equality, source hygiene, static-only root, and exact 535-byte baseline. After R, a second source-only replay must prove the full R, `parent(R) == S`, exact seven-path diff, canonical request source, unchanged runtime bytes, tracked-clean worktree, absent registered study root, and no stale target process.

The launch configuration must parse to the exact trusted qualifier command plus non-command properties `runAtGameStart=true`, `verbose=false`, `waitForProcess=true`, and `maxInitializationTimeout=120`. Only then may one tracked `qualify` invocation publish the active request and start one real CommunicationMod child. It may not call `start`, create a run lock or ledger, initialize exploration, claim a slot, or perform gameplay.

After the one shot, preserve the canonical completion or failure self-hash, file SHA-256, and size before independent replay. A passing completion is insufficient without exact 535-byte CommunicationMod restoration, equal marker/run/checkpoint/global-log observations, absent study/gameplay artifacts, a dead child PID, and a separately published verifier attestation.

R6 completion plus attestation may authorize only a later explicit `start` decision. R6 failure or any partial prefix is immutable and leaves `start`, run-lock creation, collection, OPE interpretation, gameplay-policy changes, formal training, and promotion blocked.
