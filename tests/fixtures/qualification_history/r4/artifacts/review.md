# V2 R4 Tracked Qualification Review

Date: 2026-07-18

Status: prepared for direct-child review commit; no qualifier, game, run lock, collection, OPE, or training process has started.

## Decision

The v2 registration re-rendered byte-for-byte after the tracked qualification orchestrator landed. The registration therefore remains the active canonical artifact; the historical r3 registration review remains unchanged as evidence of that failed candidate. Source snapshot S is fixed at `76ed7135ad2e8236c77b20957a0617262c9e77b6`.

The only authorized next live action is one invocation of the tracked qualifier in the previously absent r4 root. The request, this report, and the five OpenSpec files listed below must be committed together as review commit R. R is defined by all of these invariants:

- `parent(R) == S`
- `HEAD == R` at launch
- R has exactly one parent
- the exact S-to-R path set equals the request's sorted seven-path allowlist
- every changed path is an inert, non-executable review file
- registration and all 14 registered implementation files have identical bytes at S, R, and the launch worktree

R cannot be embedded in its own committed bytes. The operator must resolve its full 40-hex value after this commit and preserve it as an external launch anchor together with the request anchors below. A missing, abbreviated, stale, or mismatched R keeps qualification blocked.

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

The exact registration regression passed on 2026-07-18. A fresh dry-run produced 24 launch records, canonical SHA-256 `b59ae719f4a408409c0d3416c0c1b1b84ba24393bc4d92a8a46e137f66cab6b9`, and size 57941 bytes. It created no study artifact.

## Request Anchors

| Field | Value |
|---|---|
| Request source | `reports/noncombat_outcome_evidence_expansion_20260716_v2_r4_qualification_request.json` |
| Schema | `noncombat-outcome-evidence-qualification-request-v1` |
| Request self-hash | `f21313b80fedfccdea76c0e69d3d3d44f06289ba033159537d73f0202f3c039e` |
| Request file SHA-256 | `1e04b2a378e434c16f45cdb8a389dd527d2419ae6625d6a141e1a9fb0be4792c` |
| Request size | 5996 bytes |
| Source snapshot S | `76ed7135ad2e8236c77b20957a0617262c9e77b6` |
| Review commit R | full 40-hex direct child containing this seven-path review; resolve and pin externally after commit |
| Qualification ID | `noncombat-outcome-evidence-expansion-20260716-v2-qualification-r4` |
| Qualification root | `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r4` |
| Static config SHA-256 | `b925aca3c6c0051542ebf0e9d6c12d6def868c119e3a00fbafb0502f293937aa` |
| Static config size | 950 bytes |
| Marker boundary | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\ai_games.txt`, 15255 lines at request creation |

The r4 root was absent before preparation. Its complete pre-request inventory is exactly `qualification-config.json`; the active request, attempt, ready, release, completion, failure, manifest, trace, registered study root, run lock, and ledger are absent.

The request review allowlist is exactly:

1. `openspec/changes/add-tracked-outcome-qualification-orchestrator/tasks.md`
2. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/design.md`
3. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/proposal.md`
4. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/specs/noncombat-outcome-evidence-expansion/spec.md`
5. `openspec/changes/run-v2-known-propensity-outcome-evidence-study/tasks.md`
6. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r4_qualification_request.json`
7. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r4_qualification_review.md`

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
| `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py` | `e37440fe8aa4b4384b94f40e822921fc397335f200f6d446315e394431af2d84` | 230634 |
| `main.py` | `0740f26b096e474172fa242a848cf856152c4188ce700a2fd63311aac5ce0fa4` | 58178 |
| `scripts/run_noncombat_outcome_evidence_expansion.py` | `121a21e924ebab33c950cec9f83a6639982347b8f05acb5692962a5ae4171d1c` | 223291 |
| `spirecomm/ai/noncombat_exploration.py` | `1a075b7fff8b46ab095af4d9a6bbf3dd4f2c7d12b7115d3004b64eeffded7dc5` | 82322 |
| `spirecomm/ai/noncombat_exploration_runtime.py` | `ff013f04b6e00cbf11bf7e378fa4d72146f578d65f9c01519f68d92f1bc03030` | 19344 |
| `spirecomm/communication/study_handshake.py` | `5d61573b4d5e590cffc94d015db88794a9582524d73f9bb1eb743eb78aa0ee0f` | 25473 |

## Preserved Failures

| Identity | Failure self-hash | Failure file SHA-256 | Governing result |
|---|---|---|---|
| r1 | `ccd76824c90a9726c57b48a7f71d8bc1d8da94df6c686ae36eff10a1b72db41f` | `0677212e139270219be597e26f9e79bab30ab2c74fc5c810c41360c2d7dd545a` | immutable external log-sharing failure; no retry/start |
| r2 | `8bb9b396e129e017fd84fb4aabe7fa6d02bb51b0c7c147836dbf29e7c289c95c` | `3fbace492dd0f849bdf86deff1df97dfc4ae3b77a427545413ac48170c9c2540` | immutable 30-second cold-start implementation failure; separately fixed; no retry/start |
| r3 | `e495ce302f0ddf9628962e0d4147614a0cf9b9c7c010f256662a98eae76b033d` | `5a3c47f5b93d7c1f66b5de6c32d3af139188b60735fa36733c6b3c6ee772cfec` | valid attempt/ready, absent release, release-side external orchestration failure, no implementation defect, no retry/start |

The r3 final root inventory is `2a63cf3b7505ebf6d9e2f605eade7deec3c0afdaaa4da90ca6a99b517c82cb16`. The exact historical monitor explanation remains historical text but is not independently sufficient to constrain r4. R4 replaces split manual ready/release ownership with the tracked one-shot qualifier.

## Source Hygiene

Qualification source scanning includes ignored files and rejects untracked executable, importable, reparse, or otherwise non-inert paths. Historical test basetemps and local non-inert artifacts were preserved outside the repository at `D:\PycharmProjects\slay-the-spire-ai-test-artifact-quarantine\20260718-pre-r4` rather than deleted.

- 850 test-artifact directories were moved intact.
- 674 additional files were moved under an external recovery plan.
- Recovery plan SHA-256: `fde4b47cb73af36c6e96324f5eee6c245f90ed4c926826af777627cf50ee507f`.
- Completion record SHA-256: `9920c6b7387687c147d9e9c8abed1430d2c05331cd27c6cc1f9d4c47768e135b`.
- Post-quarantine rejected-path count: 0.

These external hygiene artifacts grant no study authority and are not request preexisting files. They remain available for restoration after the qualification/start integrity window.

## Launch And Terminal Gate

After R is committed, independent review must first prove the exact one-parent chain, allowlist diff, request replay, registration/implementation equality, tracked-clean source, and zero untracked non-inert paths. The only valid qualifier invocation supplies the exact request self-hash, file SHA-256, size, and full R through the trusted isolated launcher.

After the one shot, preserve the canonical completion or failure result self-hash, file SHA-256, and size before running the independent qualification verifier. A passing completion is not sufficient without exact terminal replay, byte-restored CommunicationMod configuration, unchanged marker/run/checkpoint/global-log snapshots, absent study/gameplay artifacts, zero surviving target processes, and a separately published verifier attestation.

R4 completion and attestation may authorize only a later explicit `start` decision. R4 failure or any partial prefix is immutable and leaves `start`, run-lock creation, collection, OPE interpretation, gameplay-policy changes, formal training, and promotion blocked.
