# R7 Offline Qualification Candidate Review

Date: 2026-07-20

Status: offline candidate only; publication and invocation are not authorized.

## Frozen Contract

- Source snapshot S: `b9e5384ed8d2d0c78fb24fa59f65c00da0a1e73a`
- Branch/upstream at render: `codex/noncombat-ope-readiness` / `b9e5384ed8d2d0c78fb24fa59f65c00da0a1e73a`
- Qualification identity: `noncombat-outcome-evidence-expansion-20260716-v2-qualification-r7`
- Qualification root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r7` (absent)
- Registered study root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2` (absent)
- External evidence root: `D:\PycharmProjects\slay-the-spire-ai-r7-qualification-evidence-20260720` (absent)
- R1-r3 remain immutable failures, r4 remains obsolete, and r5-r6 remain retired static-only identities.
- No source repair is permitted in this amendment.

## Candidate Anchors

- Config image: `reports/noncombat_outcome_evidence_expansion_20260716_v2_r7_qualification_config.json`, SHA-256 `8a4567df36c1e47d9180ece0163ea637f768aae57d7b2251ca64a80ddf3a0b26`, 949 bytes
- Request v3: `reports/noncombat_outcome_evidence_expansion_20260716_v2_r7_qualification_request.json`, self-hash `eeab6789a93f5b8fb60e384adca55c397af02e52ae03d675825a7f823aa401ff`, file SHA-256 `f2241b6a75511bc4e15a238298f5d546a918bec1fb3bfa6af2d4f1ea8ae4ae1b`, 10526 bytes
- Checklist: `reports/noncombat_outcome_evidence_expansion_20260716_v2_r7_qualification_checklist.json`, SHA-256 `3b34dabf9a3e515b267b8abb401c590f7ea8ed6e6ddbbb2c81d008ecacdb4ed2`, 52914 bytes
- Isolation baseline: `a37a8e64fff42339b9d13bcede2dba5370d678c9e08b74d1e31107ccb4d7aed4`
- Target Java/qualification Python process count: `0`
- Runner: `19c1fa94f87f867ad0da0555b6e3183ce098e56700c40d0d78a4c44e11e62653`, 363985 bytes
- Verifier: `44095dba9fab2fedda8752eca798038594ef89d2f9bd0ee9153b5b73670483f8`, 320131 bytes
- Trusted launcher code token: `1d2d0fc0b4c56f303cd5fe5e1778e878ff22be93288b112b0e435a826f396877`, 27125 bytes

The exact review commit cannot be embedded in its own tracked bytes. After the direct-child commit is created, the external review package must bind that full commit, derive the exact bootstrap envelope and launch token, reconstruct the complete CommunicationMod vector, and repeat source-only review before an external go decision.

## Proposed S-to-R Allowlist

1. `openspec/changes/qualify-r7-outcome-evidence-replacement/tasks.md`
2. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r7_qualification_checklist.json`
3. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r7_qualification_config.json`
4. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r7_qualification_request.json`
5. `reports/noncombat_outcome_evidence_expansion_20260716_v2_r7_qualification_review.md`

All paths are inert JSON, Markdown, or OpenSpec checklist content. Registration and all registered implementation files remain unchanged.

## Offline Review Boundary

The public source request loader requires the published qualification root to exist. Before publication, review therefore replays canonical bytes, request self-hash, bootstrap paths, config schema, review allowlist, implementation map, isolation baseline, root inventory image, and no-follow absences independently. After exact static publication, the official source-only loader and standalone verifier must compare the published root to these reviewed bytes before any operator invocation.

A source or protocol finding is a no-go. It must leave the external root absent before publication, or preserve and retire it after publication, and move repair to a separate regression-backed change.

## Authority

This candidate grants no authority to publish or invoke r7, start the study, create a run lock, collect trajectories, inspect outcomes, compute OPE, change policy or rewards, train, promote, or prepare r8. Only an externally anchored all-green post-R go record may permit the single publication/invocation boundary defined by the approved amendment.
