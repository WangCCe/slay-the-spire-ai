# Non-Combat Outcome Evidence Expansion V2 Registration Review

Date: 2026-07-16

OpenSpec change: `run-v2-known-propensity-outcome-evidence-study`

Status: `FROZEN_PRE_QUALIFICATION_R2`

This report records the amended pre-collection v2 candidate identity. One
bounded qualification attempt started under the original external
qualification identity and stopped before ready/release. No registered game,
run lock, ledger, gameplay action, OPE calculation, training, reward change,
gameplay-policy change, or live promotion has started.

## Historical Boundary

The standalone verifier replayed the immutable 2026-07-15 v1 root with exit
code 0 and 534 checks. No historical byte was modified.

| Item | Hash |
| --- | --- |
| Registration | `adf850f96537f01ae29f99d45a56c1d9ffcddecc33665e4c76680515ca6631c2` |
| Run lock | `b6c1a48dfb0c3ba479fe58d4c7d7d280821dd065dc4f9afacdd5ba39fadfd27f` |
| Final ledger record | `bcc971070a7b3a78fedab01b7b6c8f998e8648cb9a97ebba0ca0b9d724e868cf` |
| Finalization claim | `329d85ae12f3a5233d7a9dfcb289ba651f4fa60159c5e95f909f6d4bb163f03c` |
| Closeout | `9aec815b0e5812eedd093a49f325a566260b459df752f5a88e39fca158483252` |
| Root inventory, 59 files | `84acbb819b90761cd532a5b6bbf158e5a518141cf51fe39dbe863d0ff9d0c2e3` |

The blocked v1 root still contains none of
`registered-pool-manifest.json`, `registered-pool-samples.jsonl`,
`current-target.json`, `ope-readiness.json`, `ope-readiness.md`,
`ope-estimate.json`, or `ope-estimate.md`.

## V2 Identity

- Study ID: `noncombat-outcome-evidence-expansion-20260716-v2`
- Schema: `noncombat-outcome-evidence-registration-v2`
- Registration: `reports/noncombat_outcome_evidence_expansion_20260716_v2_registration.json`
- Artifact root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2`
- Active qualification root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r2`
- Preserved failed qualification root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification`
- Failed qualification record self-hash: `ccd76824c90a9726c57b48a7f71d8bc1d8da94df6c686ae36eff10a1b72db41f`
- Failed qualification record file SHA-256: `0677212e139270219be597e26f9e79bab30ab2c74fc5c810c41360c2d7dd545a`
- Seed base: `2026071600`
- Canonical registration hash: `86cb17077fe5dc7123307660eef4c1986dc11f48837308fed714faf88c73f22a`
- Registration file SHA-256: `2a7e937da2c63d6c235452349d3f66de5870525d578c51deccbb87a522baef6a`
- Registration bytes: `19795`
- Canonical line ending: `LF`

The registered study root and original qualification root were absent at
candidate creation. The original qualification root is now immutable failed
operational evidence; the active replacement root and registered study root
are absent at this amendment. The exact-artifact regression reconstructs the
unchanged registration bytes and hash, verifies 24 ordered unique slots and 72
unique absolute output paths, and rejects every v1 study ID, root, seed,
registration, run-lock, ledger, claim, closeout, and inventory binding. Its
TDD transition was one expected missing-file failure followed by `1 passed, 35
deselected` after canonical generation.

## Schedule And Behavior

The schedule contains 24 ordered slots of 25 attempts, for 600 scheduled
attempts. Session IDs are `s01` through `s24`, seeds are `2026071601` through
`2026071624`, and replacement slots are forbidden.

- Executable categories: `card_reward`, `shop`
- Alternative rates: `card_reward=300`, `shop=1000` basis points
- Executable alternatives: `card_reward:skip`, `shop:leave`
- Per-run alternative budget: `2`
- Shadow-only categories: `event`, `route`

The registered command is eval-only:

```text
D:\anaconda\envs\stsai\python.exe D:\PycharmProjects\slay-the-spire-ai\main.py --agent combat_rl --elite-route conservative --max-games 25 --ascension 0 --rl-version v2 --eval
```

It contains no `--train`, tuning, reward mutation, or policy-promotion flag.

## Analysis And Thresholds

- Target policy: deterministic Current
- Bootstrap: 10,000 replicates, 95 percent confidence
- Calibration: `reports/noncombat_ope_estimator_calibration_20260714.json`
- Minimum complete trajectories: `575`
- Minimum arm decisions per executable category: `50`
- Minimum nonzero-weight fraction: `1/2`
- Minimum ESS fraction: `1/2`
- Maximum normalized weight: `1/20`
- Minimum supported victories: `3`

Outcome fields remain forbidden during collection. The registered
`finalization_requires_all_slots_terminal=true` field governs only normal
pool/OPE finalization: without a global stop, every slot must be terminal. A
recorded global stop is the mandatory exception and selects the blocked branch,
which preserves the terminal prefix plus unlaunched suffix and emits no normal
pool/OPE artifact. Outcome-adaptive source, rates, thresholds, schedule, or
launch decisions are forbidden in either branch.

## Frozen Implementation Surface

The future run lock must bind these exact repository paths:

- `analysis_scripts/__init__.py`
- `analysis_scripts/noncombat_exploration_evidence.py`
- `analysis_scripts/noncombat_ope_estimate_artifacts.py`
- `analysis_scripts/noncombat_ope_estimation.py`
- `analysis_scripts/noncombat_ope_readiness.py`
- `analysis_scripts/noncombat_outcome_evidence_expansion.py`
- `analysis_scripts/verify_noncombat_ope_artifacts.py`
- `analysis_scripts/verify_noncombat_ope_estimates.py`
- `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py`
- `main.py`
- `scripts/run_noncombat_outcome_evidence_expansion.py`
- `spirecomm/ai/noncombat_exploration.py`
- `spirecomm/ai/noncombat_exploration_runtime.py`
- `spirecomm/communication/study_handshake.py`

The v2 preclaim handshake is
`noncombat-outcome-evidence-handshake-v1`. It requires an exclusive attempt
record and child-published ready record before slot claim, followed by the
parent release record. Readiness timeout is 30 seconds, release timeout is 10
seconds, and any orphaned attempt is a global stop. The exact filenames use
attempt suffix `-communication-attempt.json`, ready suffix
`-communication-ready.json`, and release suffix
`-communication-release.json`.

## Candidate Isolation

At registration time there was no Slay the Spire, Java, registered runner, or
production Python process. The only PowerShell processes were Codex's parser
and the read-only inventory command. The v2 registration path, study root, and
original qualification root were unused before generation. The registered
study root and active replacement qualification root remain absent.

The authority boundary is closed. This candidate does not authorize live
collection until focused/full offline verification, independent review, a
tracked-clean planning commit, dry-run replay, bounded no-action qualification,
and separately attested qualification all pass. It never authorizes formal RL
training, causal uplift claims, gameplay-policy changes, or promotion.

## First Qualification Failure

The original post-commit qualification used source commit
`fb1756815fd2f90bb70b6db4851aa44b8f2ad2cc`, canonical registration hash
`86cb17077fe5dc7123307660eef4c1986dc11f48837308fed714faf88c73f22a`,
and dry-run digest
`abec063a4681b915ece7f4df089b94c22916058dd4d0c3f2bcea3a96f75abd04`.
The child reached CommunicationMod coordinator construction, but the external
PowerShell monitor called `File.ReadAllText` while the child log handler held
the file and treated the resulting Windows sharing violation as fatal. The
attempt stopped before ready or release and before RL component loading, agent
creation, callbacks, gameplay, or registered slot claim.

The fail-closed audit found the registered study root, run lock, ledger, ready,
and release absent. The AI marker remained at 15,255 lines with SHA-256
`88db1899d2b442c90380f74aefcf10eab21cc9e91c917295d8c0f3d02da67a76`;
all 1,305 Ironclad run metadata records, 208 checkpoint files, and both global
logs matched the pre-smoke snapshot. CommunicationMod added only its normal
Java-properties timestamp: observed raw SHA-256
`674bf681aa63032271725a902ce43bf0455af2cd452ff8970f077f0b006484ba`
retained semantic SHA-256
`242f4e7a7f9aaeacf477a1dde26d762d840a675e017d739d997e5fb9228727a3`.
The original 505-byte baseline was restored at raw SHA-256
`374806e6386940a5945ffd03411b526d6a21c002b938bb4db253780f787b8e9a`.

The self-hashed failure record replays exactly and sets
`study_start_allowed=false` and
`same_qualification_identity_retry_allowed=false`. An independent governance
review rejected an in-place retry, found no implementation defect requiring a
new registration, and required this explicit reviewed amendment before using
the previously absent `qualification_r2` root. The replacement procedure polls
condition files and process state before ready, retries transient live-log
sharing violations, compares the active Java properties semantically, and
still requires byte-for-byte baseline restoration afterward.

## Initial Offline Verification

All Python commands used `D:\anaconda\envs\stsai\python.exe`, disabled the
pytest cache provider, and used a fresh repository basetemp.

| Scope | Final result |
| --- | --- |
| Registration, runner/monitor, handshake, finalizer, verifier | `192 passed in 484.72s` |
| Full repository | `2842 passed in 608.27s` |
| OpenSpec strict validation | `37 passed, 0 failed` |
| Python compile/import checks | passed |
| `git diff --check` | exit 0, no output |

Canonical replay returned the same 19,795 LF-only bytes, file SHA-256
`2a7e937da2c63d6c235452349d3f66de5870525d578c51deccbb87a522baef6a`,
and registration hash
`86cb17077fe5dc7123307660eef4c1986dc11f48837308fed714faf88c73f22a`.
The final historical replay again passed 534 checks and selected only the v1
`integrity_stop` branch. At that initial verification boundary, both v2
external roots remained absent.

The exact-artifact regression was observed failing before registration
generation and passing afterward. A second regression was observed failing
while the v2 registration/review paths had unspecified Git EOL semantics; the
new LF rules then passed. The final test also pins the reviewed canonical hash,
file hash, byte count, all 24 ordered slot records, all 72 exact paths, and
Windows case-insensitive path uniqueness.

## R2 Amendment Verification

The replacement-root amendment changed only this review and the existing
OpenSpec planning artifacts. The canonical registration remained 19,795 bytes
with file SHA-256
`2a7e937da2c63d6c235452349d3f66de5870525d578c51deccbb87a522baef6a`
and canonical hash
`86cb17077fe5dc7123307660eef4c1986dc11f48837308fed714faf88c73f22a`.
No registration-bound implementation file changed.

| Scope | R2 amendment result |
| --- | --- |
| Registration, runner/monitor, handshake, finalizer, verifier | `192 passed` (`178 in 467.41s` plus `14 in 6.27s`) |
| Full repository | `2842 passed in 649.76s` |
| OpenSpec strict validation | `37 passed, 0 failed` |
| Registration file replay | unchanged |
| Failed qualification record replay | self-hash `ccd76824c90a9726c57b48a7f71d8bc1d8da94df6c686ae36eff10a1b72db41f` |

An independent amendment review reported no Critical or Important finding and
approved transition to a tracked-clean replacement-qualification candidate.
It explicitly did not authorize qualification, `start`, or collection. Those
remain gated by tasks 3.3 through 3.6 and the pre-start replay in task 4.1.

## Independent Review

The first independent review found no Critical issue and three candidate-layer
findings: ambiguous all-terminal wording for the global-stop branch, missing
fixed artifact digests and Windows path uniqueness in the regression, and
omitted handshake filename suffixes in this report. No runtime implementation
defect was identified.

The findings were resolved by scoping the all-terminal field to normal pool/OPE
finalization while preserving the mandatory blocked exception, pinning both
digests plus the complete slot/path sequence, documenting all three handshake
suffixes, and extending reviewed LF rules. Targeted expansion, blocked-closeout,
and OpenSpec checks passed. The same independent reviewer then reported no
remaining Critical or Important finding and approved only the candidate commit
transition, not qualification or collection.

The later qualification-failure governance review found that the failed root
must remain immutable, that a new registration is not required without a
runtime implementation repair, and that the replacement root must be approved
explicitly rather than selected ad hoc. This amendment implements that verdict
without changing registration or runtime implementation bytes.

No registered game, run lock, ledger, successful qualification artifact, pool,
OPE result, training, reward change, gameplay-policy change, or promotion
exists or is authorized at this boundary. The failed qualification artifact is
preserved but grants no authority. Replacement qualification remains a
separate post-commit gate.
