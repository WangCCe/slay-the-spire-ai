# V2 R5 Tracked Qualification Review

Date: 2026-07-18

Status: offline candidate prepared for independent amendment review and direct-child review commit; no qualifier, game, run lock, collection, OPE, or training process has started.

## Decision

The request-bound isolation repair is frozen at source snapshot S `22cfd8b0c235af51b12911c0cb949f7e28a31ce6`. The v2 registration re-rendered byte-for-byte and remains the active canonical artifact. The old r4 static configuration and request-v1 anchors remain obsolete, unlaunched, unconsumed, and non-authorizing.

The previously absent r5 root now contains exactly one canonical static configuration file. Canonical request v2 exists only as the inert repository review source named below. It binds the source, registration, implementation map, CommunicationMod raw bytes and semantic properties, marker bytes and line count, recursive run inventory, registered checkpoint-pattern inventory, and global logs. It has not been published to the active request path and no attempt, child, handshake, terminal, or study artifact exists.

The request, this report, and the five OpenSpec files listed below must be committed together as review commit R. R is valid only if all of these invariants hold:

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

The exact registration regression passed on 2026-07-18. A fresh post-repair dry-run produced 24 launch records, canonical LF SHA-256 `be6f712f9090cae2114adcde5fa370f9c984d5c29b3b65042a1adce927fbe06a`, and canonical size 57941 bytes. It wrote no study artifact.

## Request Anchors

| Field | Value |
|---|---|
| Request source | `reports/noncombat_outcome_evidence_expansion_20260716_v2_r5_qualification_request.json` |
| Schema | `noncombat-outcome-evidence-qualification-request-v2` |
| Request self-hash | `b80b5311018c6c39de6df55c8e1d9090826e07bbd606711b4d0c4d68b4d1cfce` |
| Request file SHA-256 | `40e978059c31f90c2da52435d50193deea95b1f3f19c28a865ef96f80c20ed26` |
| Request size | 8813 bytes |
| Isolation baseline hash | `f9902d1403bdc73101a1c665e06dd3e1d717c1d4a86faa02744fd168ffbfea43` |
| Source snapshot S | `22cfd8b0c235af51b12911c0cb949f7e28a31ce6` |
| Review commit R | full 40-hex direct child containing this seven-path review; resolve and pin externally after commit |
| Qualification ID | `noncombat-outcome-evidence-expansion-20260716-v2-qualification-r5` |
| Qualification root | `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r5` |
| Static config SHA-256 | `98e71368dba46a76bbf129e036de0dd8b290dff7e2066ede97d7f747a330c8f6` |
| Static config size | 949 bytes |
| Marker boundary | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\ai_games.txt`, 15255 lines at request creation |

The complete pre-request r5 inventory is exactly `qualification-config.json`. The active request, attempt, ready, release, completion, failure, manifest, trace, registered study root, run lock, and ledger are absent.

The request review allowlist is exactly:

1. `openspec/changes/add-tracked-outcome-qualification-orchestrator/tasks.md`
2. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/design.md`
3. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/proposal.md`
4. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/specs/noncombat-outcome-evidence-expansion/spec.md`
5. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/tasks.md`
6. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r5_qualification_request.json`
7. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r5_qualification_review.md`

## Isolation Baseline

| Resource | Bound observation |
|---|---|
| CommunicationMod config | SHA-256 `374806e6386940a5945ffd03411b526d6a21c002b938bb4db253780f787b8e9a`; 505 bytes; exact raw bytes plus `command`, `runAtGameStart`, `verbose`, and `waitForProcess` properties |
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

| Identity | Failure self-hash | Failure file SHA-256 | Governing result |
|---|---|---|---|
| r1 | `ccd76824c90a9726c57b48a7f71d8bc1d8da94df6c686ae36eff10a1b72db41f` | `0677212e139270219be597e26f9e79bab30ab2c74fc5c810c41360c2d7dd545a` | immutable external log-sharing failure; no retry/start |
| r2 | `8bb9b396e129e017fd84fb4aabe7fa6d02bb51b0c7c147836dbf29e7c289c95c` | `3fbace492dd0f849bdf86deff1df97dfc4ae3b77a427545413ac48170c9c2540` | immutable 30-second cold-start implementation failure; separately fixed; no retry/start |
| r3 | `e495ce302f0ddf9628962e0d4147614a0cf9b9c7c010f256662a98eae76b033d` | `5a3c47f5b93d7c1f66b5de6c32d3af139188b60735fa36733c6b3c6ee772cfec` | valid attempt/ready, absent release, release-side external orchestration failure; no retry/start |
| r4 | request-v1 self-hash `f21313b80fedfccdea76c0e69d3d3d44f06289ba033159537d73f0202f3c039e` | request file SHA-256 `1e04b2a378e434c16f45cdb8a389dd527d2419ae6625d6a141e1a9fb0be4792c` | static config and prep-only request source; never committed as R, published, launched, or consumed; permanently obsolete |

The r3 final root inventory remains `2a63cf3b7505ebf6d9e2f605eade7deec3c0afdaaa4da90ca6a99b517c82cb16`. None of r1-r4 may be retried, pooled, or used as qualification/start authority.

## Verification And Hygiene

The isolation repair at S passed:

- qualification-focused slice: 253 passed, 128 deselected in 675.66 seconds
- full Windows suite: 3120 passed in 1355.82 seconds
- strict OpenSpec validation: 40 passed, 0 failed
- Python compile checks and `git diff --check`
- independent read-only review: ready, with same-read derivation, full qualifier silence, v1 live rejection, and child protocol `fileno()` behavior checked

Qualification source scanning includes ignored files and rejects untracked executable/importable paths and reparse points. Earlier test artifacts remain preserved outside the repository under `D:\PycharmProjects\slay-the-spire-ai-test-artifact-quarantine\20260718-pre-r4` and `20260718-post-isolation-s-22cfd8b0c`. Before request generation, 15 newly recreated `__pycache__` directories were moved intact to `20260718-pre-r5-request-pyc`; no file was deleted. The successful generator ran with bytecode writes disabled.

At request preparation, the registered study root was absent, the r5 root contained only its static config, and no target Slay the Spire, Java, or repository production Python process was observed. These observations grant no live authority and must be repeated from tracked-clean R.

## Launch And Terminal Gate

Independent amendment review must first prove the request schema and anchors, exact one-parent chain design, allowlist, registration/implementation equality, tracked source hygiene, and absence of active control files. After R is committed, a second replay must prove the full R, `parent(R) == S`, exact seven-path diff, canonical request source, unchanged runtime bytes, tracked-clean worktree, absent registered study root, and no stale target process.

Only then may one tracked `qualify` invocation publish the active request and start one real CommunicationMod child. The invocation must use the fixed stdlib `python -I -S -c` trusted launcher and externally supply the full R, request self-hash, request file SHA-256, and request size. It may not call `start`, create a run lock or ledger, initialize exploration, claim a slot, or perform gameplay.

After the one shot, preserve the canonical completion or failure result self-hash, file SHA-256, and size before independent replay. A passing completion is insufficient without byte-restored CommunicationMod configuration, equal marker/run/checkpoint/global-log observations, absent study/gameplay artifacts, a dead child PID, and a separately published verifier attestation.

R5 completion plus attestation may authorize only a later explicit `start` decision. R5 failure or any partial prefix is immutable and leaves `start`, run-lock creation, collection, OPE interpretation, gameplay-policy changes, formal training, and promotion blocked.
