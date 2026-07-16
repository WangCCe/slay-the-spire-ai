# Non-Combat Outcome Evidence Expansion V2 Registration Review

Date: 2026-07-16

OpenSpec change: `run-v2-known-propensity-outcome-evidence-study`

Status: `FROZEN_PRE_QUALIFICATION`

This report records the pre-collection v2 candidate identity. No registered
game, qualification smoke, run lock, ledger, OPE calculation, training,
reward change, gameplay-policy change, or live promotion has started.

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
- Qualification root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260716_v2_qualification`
- Seed base: `2026071600`
- Canonical registration hash: `86cb17077fe5dc7123307660eef4c1986dc11f48837308fed714faf88c73f22a`
- Registration file SHA-256: `2a7e937da2c63d6c235452349d3f66de5870525d578c51deccbb87a522baef6a`
- Registration bytes: `19795`
- Canonical line ending: `LF`

Both external roots were absent at candidate creation. The exact-artifact
regression reconstructs the committed bytes and hash, verifies 24 ordered
unique slots and 72 unique absolute output paths, and rejects every v1 study
ID, root, seed, registration, run-lock, ledger, claim, closeout, and inventory
binding. Its TDD transition was one expected missing-file failure followed by
`1 passed, 35 deselected` after canonical generation.

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
and the read-only inventory command. The v2 registration path and both external
roots were unused before generation; the external roots remain absent.

The authority boundary is closed. This candidate does not authorize live
collection until focused/full offline verification, independent review, a
tracked-clean planning commit, dry-run replay, bounded no-action qualification,
and separately attested qualification all pass. It never authorizes formal RL
training, causal uplift claims, gameplay-policy changes, or promotion.

## Offline Verification

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
`integrity_stop` branch. Both v2 external roots remained absent.

The exact-artifact regression was observed failing before registration
generation and passing afterward. A second regression was observed failing
while the v2 registration/review paths had unspecified Git EOL semantics; the
new LF rules then passed. The final test also pins the reviewed canonical hash,
file hash, byte count, all 24 ordered slot records, all 72 exact paths, and
Windows case-insensitive path uniqueness.

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

No game, run lock, ledger, qualification artifact, pool, OPE result, training,
reward change, gameplay-policy change, or promotion exists or is authorized at
this boundary. Qualification remains a separate post-commit gate.
