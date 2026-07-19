# Non-Combat Outcome Evidence Expansion V2 Registration Review

Date: 2026-07-17

OpenSpec change: `run-v2-known-propensity-outcome-evidence-study`

Status: `FROZEN_PRE_QUALIFICATION_R3`

This report records the second amended pre-collection v2 candidate identity.
Two bounded qualification identities are immutable failures: r1 stopped on an
external Windows log-sharing error before protocol ready, while r2 exchanged
protocol ready but exceeded the superseded 30-second child readiness deadline
before the first callback-free state. The implementation defect was repaired
and verified separately in commit `79cf98f892ec19294cc85cf592ae70b4be425fba`.
No registered game, run lock, ledger, gameplay action, OPE calculation,
training, reward change, gameplay-policy change, or live promotion has started.

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
- Active qualification root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r3`
- Preserved r2 failure root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification_r2`
- R2 failure-record self-hash: `8bb9b396e129e017fd84fb4aabe7fa6d02bb51b0c7c147836dbf29e7c289c95c`
- R2 failure-record file SHA-256: `3fbace492dd0f849bdf86deff1df97dfc4ae3b77a427545413ac48170c9c2540`
- R2 ten-file root inventory SHA-256: `d1bf1c7901e3a324b849337414ee12b2f900d086cbc110a6a93ca08545858833`
- Preserved r1 failure root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification`
- R1 failure-record self-hash: `ccd76824c90a9726c57b48a7f71d8bc1d8da94df6c686ae36eff10a1b72db41f`
- R1 failure-record file SHA-256: `0677212e139270219be597e26f9e79bab30ab2c74fc5c810c41360c2d7dd545a`
- R1 nine-file root inventory SHA-256: `7fcacefddd99573929aac654044f4ecbc898ef530062977e375696d6697db600`
- Seed base: `2026071600`
- Canonical registration hash: `7df8036e111fb55ece15154796d494ea857a74984c9d1a224c2b61f8fc710ace`
- Registration file SHA-256: `a0e282699ede7d1ea38b2d81f029ce5e823b924d81c5ca7cdbc9a45ddc2eb6c2`
- Registration bytes: `19796`
- Superseded registration hash: `86cb17077fe5dc7123307660eef4c1986dc11f48837308fed714faf88c73f22a`
- Superseded registration file SHA-256: `2a7e937da2c63d6c235452349d3f66de5870525d578c51deccbb87a522baef6a`
- Superseded registration bytes: `19795`
- Canonical line ending: `LF`

The registered study root and r3 qualification root are absent at this
amendment. The r1 and r2 roots are immutable failed operational evidence and
cannot be retried or interpreted as launch authority. The exact-artifact
regression first failed against the superseded 30-second bytes, then passed
after deterministic regeneration under the 120-second builder. It reconstructs
the current registration bytes and hash, verifies 24 ordered unique slots and
72 unique absolute output paths, rejects every v1 binding, and proves the
current identity differs from the superseded hash, file hash, and byte count.

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

The r3 candidate is regenerated from the post-fix implementation baseline
`79cf98f892ec19294cc85cf592ae70b4be425fba`. The final tracked amendment
commit will contain this registration and review; qualification must bind that
final HEAD plus the following file hashes, and must reject any mismatch:

| Registered implementation path | SHA-256 | Bytes |
| --- | --- | ---: |
| `analysis_scripts/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `0` |
| `analysis_scripts/noncombat_exploration_evidence.py` | `ba6e46c2c8418e9d47f059c02d35e71a2d65165a27d5b3b68e43cb5c43d04016` | `44201` |
| `analysis_scripts/noncombat_ope_estimate_artifacts.py` | `2486b7589b221193059e615ff3a6c5aa4573cd5017e800adfec8f51e9a52b98e` | `17242` |
| `analysis_scripts/noncombat_ope_estimation.py` | `39e4b981348918ec8ab3e18c23f62f261be6a905d4b4c9826cfc3cae7e8bf370` | `36646` |
| `analysis_scripts/noncombat_ope_readiness.py` | `b62bd274c41a56ad3721c5390736c9d19171fe6037fd8edb278f848f3adf677d` | `58877` |
| `analysis_scripts/noncombat_outcome_evidence_expansion.py` | `f73708530251ff75b411eeb0ad8254b4782e2548fda257f530305b2de29d3256` | `125725` |
| `analysis_scripts/verify_noncombat_ope_artifacts.py` | `5e5e4eb2b7090fb89e57b2634dc4289bbcb4b7c81857d05d15fd22bfea927519` | `33629` |
| `analysis_scripts/verify_noncombat_ope_estimates.py` | `de0e85eca294725adc9553e7870528f69777f248a39630891e253c39a1e52991` | `52027` |
| `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py` | `14187beacdc02684343067f03c5299e21b4708a6522cc5b451219d200767f305` | `139874` |
| `main.py` | `40631676035666c4255dbef2c75aa64c9ed5c282767c348b64684bbd8f10ba9c` | `50569` |
| `scripts/run_noncombat_outcome_evidence_expansion.py` | `278f32689d59c9fe9e800e976f6f037dbf5b3353f0bdd5a44582bca188926c30` | `93196` |
| `spirecomm/ai/noncombat_exploration.py` | `1a075b7fff8b46ab095af4d9a6bbf3dd4f2c7d12b7115d3004b64eeffded7dc5` | `82322` |
| `spirecomm/ai/noncombat_exploration_runtime.py` | `ff013f04b6e00cbf11bf7e378fa4d72146f578d65f9c01519f68d92f1bc03030` | `19344` |
| `spirecomm/communication/study_handshake.py` | `5d61573b4d5e590cffc94d015db88794a9582524d73f9bb1eb743eb78aa0ee0f` | `25473` |

The v2 preclaim handshake is
`noncombat-outcome-evidence-handshake-v1`. It requires an exclusive attempt
record and child-published ready record before slot claim, followed by the
parent release record. Readiness timeout is 120 seconds, release timeout is 10
seconds, and any orphaned attempt is a global stop. The exact filenames use
attempt suffix `-communication-attempt.json`, ready suffix
`-communication-ready.json`, and release suffix
`-communication-release.json`.

## Candidate Isolation

At this amendment boundary there is no Slay the Spire, Java, registered runner,
or production Python process. Both failed qualification roots are preserved;
the registered study root and active r3 qualification root remain absent. The
CommunicationMod baseline is restored at raw SHA-256
`374806e6386940a5945ffd03411b526d6a21c002b938bb4db253780f787b8e9a`
and semantic SHA-256
`7341f96c64a633ed3b037ef499dd5b81c3355400c28c0f74c2afb6e83b9bdf51`.

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

## Second Qualification Failure And Timeout Repair

The r2 qualification used source commit
`0da07cdc4a23631aa06757da6af7a8386620fe2e`, the superseded registration
hash `86cb17077fe5dc7123307660eef4c1986dc11f48837308fed714faf88c73f22a`,
and dry-run digest
`8f870da8a337be4dafd2ac609e46ff349aaf08a267e73a0ba571e0bcb3e3cdd6`.
The child queued protocol ready and CommunicationMod received it, but the first
callback-free state did not arrive before the registered 30-second deadline.
The child failed closed before study ready/release, RL component loading, agent
creation, gameplay, or registered slot claim.

The r2 failure record replays at self-hash
`8bb9b396e129e017fd84fb4aabe7fa6d02bb51b0c7c147836dbf29e7c289c95c`
and file SHA-256
`3fbace492dd0f849bdf86deff1df97dfc4ae3b77a427545413ac48170c9c2540`.
The preserved game log has SHA-256
`efe5b85ea7ff27689ded3eb082da81447950ebc3d675e27e43bb8955f42b8f29`;
the complete ten-file root inventory has SHA-256
`d1bf1c7901e3a324b849337414ee12b2f900d086cbc110a6a93ca08545858833`.
The registered study root, run lock, ledger, gameplay evidence, AI-marker
mutation, checkpoint mutation, global-log mutation, and surviving process were
all absent. CommunicationMod was restored byte-for-byte to the 505-byte
baseline with raw SHA-256
`374806e6386940a5945ffd03411b526d6a21c002b938bb4db253780f787b8e9a`.

Because r2 proved an implementation defect, its registration and root are
immutable and grant no launch authority. The separate
`fix-cold-start-study-handshake-timeout` change reproduced a 45-second cold
state, raised the fixed readiness deadline to 120 seconds, preserved release
10, made observations at or after either exact deadline fail closed, and
completed in commit `79cf98f892ec19294cc85cf592ae70b4be425fba`.
The current registration is therefore a newly rendered contract rather than a
timeout override on the superseded bytes.

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
remained gated by tasks 3.3 through 3.6 and the pre-start replay in task 4.1 at
that historical boundary.

## 120-Second R3 Amendment

After the r2 defect fix, the exact-artifact regression was restored to require
the current builder output. It failed against the old committed artifact at the
first changed handshake-bound byte, then passed after deterministic generation
of the 19,796-byte LF-only artifact. The resulting identity is:

- Registration hash: `7df8036e111fb55ece15154796d494ea857a74984c9d1a224c2b61f8fc710ace`
- Registration file SHA-256: `a0e282699ede7d1ea38b2d81f029ce5e823b924d81c5ca7cdbc9a45ddc2eb6c2`
- Readiness/release deadlines: `120/10` seconds
- Implementation baseline: `79cf98f892ec19294cc85cf592ae70b4be425fba`
- Authorized next qualification identity: `noncombat_outcome_evidence_expansion_20260716_v2_qualification_r3`

The study ID, study root, seed schedule, 24-by-25 slot sequence, behavior rates,
alternative budget, deterministic-Current target, estimator, thresholds,
command, and release deadline are byte-for-byte or value-for-value unchanged.
Only the reviewed readiness contract, affected registration hash, and
registration file identity changed. Both failed roots and the superseded
registration identity remain historical evidence.

| Scope | R3 amendment result |
| --- | --- |
| Exact registration red/green | expected failure on superseded bytes; `1 passed in 1.28s` after regeneration |
| Review digest red/green | expected failure on one malformed 62-character copied digest; `1 passed in 0.82s` after correction |
| Registration, runner/monitor, handshake, finalizer, verifier | `201 passed in 506.06s` |
| Full repository | `2851 passed in 666.10s` |
| OpenSpec strict validation | `38 passed, 0 failed` |
| Python compile/import checks | passed |
| `git diff --check` | exit 0, no output |
| External boundary replay and r3/study absence | both failed roots exact; baseline exact; r3/study absent; no target process |

No r3 directory, live game process, run lock, ledger, registered slot, or study
artifact may be created until every pending row passes, independent review has
no unresolved Critical or Important finding, and the amendment is committed as
a tracked-clean candidate.

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

The r1 qualification-failure governance review found that the failed root must
remain immutable, that a new registration was not required while no runtime
implementation binding changed, and that the replacement root had to be
approved explicitly rather than selected ad hoc. The later r2 evidence changed
that premise by proving a timeout implementation defect. The separate repair
and this regenerated registration follow the stricter defect branch: preserve
r2, fix under regression, regenerate all affected bindings, and explicitly
authorize only a previously absent r3 identity.

The first independent review of this 120-second r3 amendment found no Critical
issue. Its one Important finding was that the recorded focused/full results
predated the final review-digest regression; two Minor findings requested exact
implementation-table replay and three independent superseded-identity
inequalities. The tests were strengthened, the malformed digest regression was
recorded, and the final tree then passed `201` focused tests and `2851` full
repository tests. Final independent re-review reported no Critical, Important,
or Minor finding and returned `Ready to commit: Yes`; this status therefore
authorizes only the tracked-clean r3 candidate commit, not r3 execution.

No registered game, run lock, ledger, successful qualification artifact, pool,
OPE result, training, reward change, gameplay-policy change, or promotion
exists or is authorized at this boundary. Both failed qualification artifacts
are preserved but grant no authority. R3 qualification remains a separate
post-commit gate.
