# Non-Combat Outcome Evidence Expansion Closeout

Date: 2026-07-16

Status: `BLOCKED`

The fixed study stopped fail-closed after slot 14. It did not unblind outcomes,
build a registered pool, run OPE, or authorize training or promotion.

## Evidence Boundary

Only the committed registration plus the external run lock, append-only ledger,
blinded monitor, finalization claim, and blocked closeout determine this study's
`BLOCKED` status. The post-study isolation snapshot and live-log hashes are
Task 8.3 operational audit evidence; they are not registered finalization
inputs. Configuration restoration and the local sandbox diagnostic are
post-lock operator actions and cannot change, cure, or strengthen the study
result.

## Registered Identity

- Study ID: `noncombat-outcome-evidence-expansion-20260715`
- Registration hash: `adf850f96537f01ae29f99d45a56c1d9ffcddecc33665e4c76680515ca6631c2`
- Source commit: `fb21f06888c9019be382ae4f4f618aa037e691ef`
- Run-lock hash: `b6c1a48dfb0c3ba479fe58d4c7d7d280821dd065dc4f9afacdd5ba39fadfd27f`
- Artifact root: `D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260715`

## Collection Accounting

| Slots | Terminal state | Complete marker joins |
|---|---|---:|
| 01-02 | completed | 50 |
| 03 | interrupted | 22 |
| 04-12 | completed | 225 |
| 13 | interrupted after host reboot | 8 |
| 14 | interrupted before gameplay trace | 0 |
| 15-24 | unlaunched after global stop | 0 |

Fourteen registered slots launched once and became terminal. Their ledger rows
contain 305 complete trajectory markers. No slot was restarted or replaced.

The last successful blinded monitor render had 14 launched and 14 terminal
slots and reported only `terminal_slot_structure_invalid_14`. The append-only
ledger then recorded the same string as its global stop reason. Relevant hashes:

- Study ledger SHA-256: `60e0afa15c759672f0ed4f5cc79e7bf528fd12cc1512e3ba26cfbc88a9645a78`
- Blinded monitor SHA-256: `a81a512486287f71e1443fd867fa86d0e62998a06c634c46776ae880f8e5c121`

## Registered Recovery State

The host reboot interrupted slot 13. With no study process chain remaining, its
marker interval was recovered append-only as `15247..15255`, yielding eight
complete trajectories and no replacement attempt.

Slot 14 then launched once under the unchanged lock. It reached the game main
menu and created its registered manifest, but produced no gameplay trace or new
AI marker. The ledger therefore records marker interval `15255..15255`, zero
complete trajectories, and terminal status `interrupted`.

The marker bounds and terminal states above come from the registered ledger;
the missing slot 14 trace and structural blocker come from the blinded monitor.

### Operational Log Observation

The earlier slot 13 failure appears in both logs as a broken CommunicationMod
pipe at 2026-07-15 21:24 local time. The slot 14 timeout appears in
`ai_debug.log` at 2026-07-16 00:36:48 local time, after 45 startup polls and a
final `Communication Mod not responding` message. Final log hashes are:

- `ai_debug.log`: `f1865917572af46d0ff25f0f0dd73ba2c124f6b3fbcc89935f2493efc96e8847`
- `communication_mod_errors.log`: `bd8b833a075488d834f9af33075d48c56258801a07e3e9a41714e023901b7197`

These mutable live logs were inspected only for Task 8.3 protocol diagnosis.
They are not frozen registered evidence and were not used to select the global
stop reason, continuation rule, or closeout status.

## Blocked Finalization

The finalization claim has mode `integrity_stop`. The deterministic closeout is
`blocked` with stop reason `terminal_slot_structure_invalid_14` and closeout
hash `9aec815b0e5812eedd093a49f325a566260b459df752f5a88e39fca158483252`.

- Claim file SHA-256: `3b2a2f1bfc14b4af79c7fd904ef370d59918f93423542b02eef1aede893242fb`
- Closeout JSON SHA-256: `fbed42c3e5e7d8f4a29eda691ef373c7a065080d33d5253feee2f62440f2b675`
- Closeout Markdown SHA-256: `5ea4ac689f5dff4461b82935fa5c064de3fa41ef13a9b847e79faef3dfdd92d3`

By contract, the blocked path wrote no registered pool, target, readiness,
estimate, bootstrap, influence, or comparison artifact. Every authority gate in
the closeout is false, including outcome-evidence expansion, OPE estimate,
policy comparison, causal uplift, formal non-combat RL training, reward design,
and live policy promotion.

## Independent Verification Gap

The frozen standalone verifier implementation has SHA-256
`15ea3fc266a94d76cf96b44109ec6788e4fc9ff9f1ac4390edb02c0d3618c618`.
It was run against the blocked closeout while the source, study configuration,
and checkpoint snapshot still matched the run lock. It exited nonzero with:

```text
[outcome-evidence-verifier] normal closeout has a global stop
```

The verifier implements only the normal all-slot closeout and rejects the
registered global-stop state before checking the blocked claim and closeout.
This is a frozen implementation gap, not a passing verification. No later code
change can retroactively become the run-locked verifier for this study. A fresh
change must add and test blocked-closeout verification before another
registration is created.

## Operational Isolation Audit

The Task 8.3 post-study isolation artifact, which is outside the registered
finalization output set, has SHA-256
`dcd1348dd1ee5c9fcabdae3933e86d4f2314804df8af452731b8d4a99e04049d`.
It confirms:

- CommunicationMod semantic SHA-256 remained
  `961d8df7edd68461feebb830ee700a012f8bccf994ed00ea4eeae5a978c6d06d`.
- All 208 checkpoint path, size, and content hashes match the run lock.
- No training or checkpoint mutation occurred.

This audit was captured before tracked source changed and closes the run-lock
window operationally, but it does not alter the registered blocked closeout.

## Post-Lock Operator Actions

After the isolation snapshot, CommunicationMod was restored byte-for-byte from
`config.properties.pre-outcome-evidence-20260715.bak`. The restored file
SHA-256 is `374806e6386940a5945ffd03411b526d6a21c002b938bb4db253780f787b8e9a`
and points to the ordinary bounded eval command, not the study wrapper.

The first local finalizer process was denied write access to the external
artifact root by the Codex sandbox before any claim or final artifact existed.
A read-only `py-spy` stack showed it retrying `tempfile.mkstemp`; the process was
stopped, absence of every final artifact was rechecked, and the same frozen
finalizer was then run outside the sandbox. This tooling observation explains
the local execution sequence only. It is not registered study evidence and was
not used to determine the blocker or any gate.

## Authority Boundary

This closeout does not support a policy-quality or causal claim. It does not
authorize formal non-combat RL, reward design, gameplay-policy edits, Bottled
live actions, or live promotion. The existing artifact root is permanently
blocked and must never be resumed, extended, or pooled into a later study.

Before another registered collection, the repository needs a separate fix for
blocked-closeout verification and a no-game CommunicationMod handshake that can
fail before a slot is claimed. Any comparable retry requires a new source lock,
new artifact root, and new registration.
