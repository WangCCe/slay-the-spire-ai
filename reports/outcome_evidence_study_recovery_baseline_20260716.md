# Outcome-Evidence Study Recovery Baseline

Date: 2026-07-16

## Scope

This report freezes the read-only baseline for recovering verifier and launch
safety around the blocked study `noncombat-outcome-evidence-expansion-20260715`.
No file under the study artifact root was written while collecting this
baseline. The study remains permanently blocked and is not eligible for resume,
replacement slots, OPE, training, reward work, or promotion decisions.

Artifact root:

`D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260715`

## Registration And Run Lock

| Item | Value |
| --- | --- |
| Registration schema | `noncombat-outcome-evidence-registration-v1` |
| Registration file SHA-256 | `c0a0b2cf1545965ebca8b24aa2193cc70c8d173ffc71fd993b839b7dbf30f215` |
| Canonical registration hash | `adf850f96537f01ae29f99d45a56c1d9ffcddecc33665e4c76680515ca6631c2` |
| Run-lock file SHA-256 | `6ec3584a691586e541368d18408bbb3decdf3e57cfc335c5dc3b50a9ef4950ee` |
| Canonical run-lock hash | `b6c1a48dfb0c3ba479fe58d4c7d7d280821dd065dc4f9afacdd5ba39fadfd27f` |
| Run-lock source commit | `fb21f06888c9019be382ae4f4f618aa037e691ef` |
| Baseline checkout commit | `0fd0ff7752356e3beafaf7bf13d9858c45faa66a` |

## Blocked Ledger State

| Item | Value |
| --- | --- |
| Ledger file SHA-256 | `60e0afa15c759672f0ed4f5cc79e7bf528fd12cc1512e3ba26cfbc88a9645a78` |
| Final ledger record hash | `bcc971070a7b3a78fedab01b7b6c8f998e8648cb9a97ebba0ca0b9d724e868cf` |
| Terminal slots | `14` |
| Completed slots | `11` |
| Interrupted slots | `3` |
| Unlaunched slots | `10` |
| Complete trajectories | `305` |
| Marker range | `14950..15255` |
| Global stop | `terminal_slot_structure_invalid_14` |

The marker delta is exactly 305 and equals the sum of terminal-slot
`complete_trajectories`. Slot 14 is terminal and interrupted with zero new
trajectories; it is not active or launchable.

## Finalization Artifacts

| Artifact | File SHA-256 | Embedded self-hash |
| --- | --- | --- |
| `finalization-claim.json` | `3b2a2f1bfc14b4af79c7fd904ef370d59918f93423542b02eef1aede893242fb` | `329d85ae12f3a5233d7a9dfcb289ba651f4fa60159c5e95f909f6d4bb163f03c` |
| `outcome-evidence-closeout.json` | `fbed42c3e5e7d8f4a29eda691ef373c7a065080d33d5253feee2f62440f2b675` | `9aec815b0e5812eedd093a49f325a566260b459df752f5a88e39fca158483252` |
| `outcome-evidence-closeout.md` | `5ea4ac689f5dff4461b82935fa5c064de3fa41ef13a9b847e79faef3dfdd92d3` | n/a |
| `blinded-monitor.json` | `a81a512486287f71e1443fd867fa86d0e62998a06c634c46776ae880f8e5c121` | n/a |
| `blinded-monitor.md` | `b359518c60d4082d90dd1ac6d0b32bed50dbc63c679e53f848aba60b682c1ab0` | n/a |
| `post-study-isolation.json` | `dcd1348dd1ee5c9fcabdae3933e86d4f2314804df8af452731b8d4a99e04049d` | n/a |

The claim mode is `integrity_stop`; the closeout status is `blocked`, and its
integrity-stop reason is `terminal_slot_structure_invalid_14`.

## Deliberately Absent Artifacts

The following files do not exist and must remain absent for this blocked study:

- `registered-pool-manifest.json`
- `registered-pool-samples.jsonl`
- `current-target.json`
- `ope-readiness.json`
- `ope-readiness.md`
- `ope-estimate.json`
- `ope-estimate.md`
- `bootstrap-distribution.json`
- `influence-diagnostics.json`
- `policy-comparison.json`

## Root Inventory Anchor

The root contains 59 regular files. The inventory digest is
`84acbb819b90761cd532a5b6bbf158e5a518141cf51fe39dbe863d0ff9d0c2e3`.
It is SHA-256 over UTF-8, LF-terminated rows sorted by filename, where each row
is `filename|size|sha256`.

## Verifier Baseline

Running the current verifier from the baseline checkout exits 2 before closeout
reconstruction with:

```text
[outcome-evidence-verifier] Git HEAD differs from the run lock
```

At a matching source anchor, the current verifier has a second normal-only
assumption: `_verify_ledger` rejects any global stop as `normal closeout has a
global stop`. The synthetic regression for this change must demonstrate that a
valid registered blocked closeout passes independent replay, while the existing
normal-closeout control remains green.

## Recovery Acceptance

The recovery implementation may read and independently verify these artifacts,
but it must not mutate or resume them. Before closeout of the implementation
change, this inventory anchor and all key hashes above will be recomputed. Any
drift is a blocker, not a repair opportunity.

## Recovery Verification Result

After the independent blocked branch was implemented, the standalone Windows
CLI replayed the immutable registration with exit code 0 and reported:

| Item | Value |
| --- | --- |
| Independent checks | `534` |
| Closeout mode | `integrity_stop` |
| Registration hash | `adf850f96537f01ae29f99d45a56c1d9ffcddecc33665e4c76680515ca6631c2` |
| Run-lock hash | `b6c1a48dfb0c3ba479fe58d4c7d7d280821dd065dc4f9afacdd5ba39fadfd27f` |
| Final ledger record hash | `bcc971070a7b3a78fedab01b7b6c8f998e8648cb9a97ebba0ca0b9d724e868cf` |
| Closeout hash | `9aec815b0e5812eedd093a49f325a566260b459df752f5a88e39fca158483252` |
| Verifier file SHA-256 | `251495635cd56815d6df79e8198c252aee0e91420ea77f1987648bd47f8981de` |

The complete verifier module passed `46` tests in `352.40s`, including normal
replay, historical blocked replay after checkout movement, tamper rejection,
forbidden-output rejection, and import independence. Normal closeouts still
require current HEAD, tracked source, CommunicationMod configuration, and
checkpoint inventory to match the run lock.

The post-replay root inventory remained 59 files with digest
`84acbb819b90761cd532a5b6bbf158e5a518141cf51fe39dbe863d0ff9d0c2e3`.
Every key file hash remained unchanged, and every deliberately absent artifact
remained absent. The verifier pass is a blocked-closeout integrity result only;
it does not authorize pooling, OPE, training, reward design, or promotion.
