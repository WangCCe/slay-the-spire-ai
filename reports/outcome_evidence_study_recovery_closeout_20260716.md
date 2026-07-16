# Outcome-Evidence Study Recovery Closeout

Date: 2026-07-16

OpenSpec change: `harden-outcome-evidence-study-recovery`

## Result

The recovery implementation is complete and verified. The historical v1 study
remains permanently blocked and byte-preserved. Future v2 studies now require
the real CommunicationMod child to publish bound readiness before a ledger slot
is claimed, and the standalone verifier independently replays the resulting
attempt, ready, release, and marker-bound ledger evidence.

This result does not create a registration or authorize collection, pooling,
OPE, training, reward design, gameplay-policy changes, or live promotion.

## Independent Review Disposition

| Finding | Disposition |
| --- | --- |
| Final handshake paths were visible before their bytes were complete. | Accepted. Records are now fsynced in a same-directory temporary file and exposed once through an exclusive hard link. |
| `run-next` validated the run lock before recovering an already claimed slot. | Accepted. Active-slot recovery now runs first, so lock drift cannot strand a claimed slot. |
| The run lock, child liveness, marker, config, and output boundary could drift after readiness. | Accepted. The runner revalidates the run lock before claim, checks liveness before and after claim, and rechecks marker/config/output state immediately before release. |
| Child termination failures were silently discarded. | Accepted. Failed termination and kill details are appended to the terminal recovery and global-stop reason. |
| The independent v2 verifier ignored handshake artifacts and only accepted legacy empty `slot_started` payloads. | Accepted. The verifier now reconstructs v2 records without importing the runtime handshake or runner modules, while v1 remains read-only compatible. |
| Any all-terminal ledger followed by a global stop should be rejected as branch laundering. | Not adopted. A post-collection integrity failure before finalization legitimately selects an all-authority-false integrity-stop closeout. |
| Marker/output/claim publication should be atomically committed as one cross-file transaction. | Not adopted. The filesystem contract has no cross-file transaction; before/after guards narrow and detect the remaining claim micro-window. |
| Add a new release-consumption acknowledgment protocol. | Deferred. It would change the registered protocol and child accounting contract; the present change only hardens the approved attempt/ready/release design. |

## Automated Verification

All commands used Windows Python
`D:\anaconda\envs\stsai\python.exe`, disabled pytest's cache provider, and used
fresh writable repository basetemps.

| Scope | Result |
| --- | --- |
| Handshake module | `20 passed in 1.98s` |
| Registered runner | `75 passed in 31.48s` |
| Independent verifier | `47 passed in 447.65s` |
| Main startup, exploration runtime, expansion, finalizer, gate, and pool | `110 passed in 37.45s` |
| Full repository | `2841 passed in 682.26s` |

Strict OpenSpec validation, `git diff --check`, Python compilation, imports, and
independent/runtime handshake schema bindings all passed. The verifier's static
import test forbids imports from the finalizer, runner, and runtime handshake
module.

## Bounded CommunicationMod Smoke

One counted no-action smoke used
`C:\Users\20571\AppData\Local\Temp\sts-handshake-smoke-20260716-closeout-r3`.
The real child PID was `32948`. CommunicationMod delivered a state with
callbacks disabled, the child published ready, the parent published release,
and the child reached `Loading RL components...`; it was then stopped before
agent creation, callbacks, or gameplay.

| Record | Embedded self-hash |
| --- | --- |
| Attempt | `854d0c9241a118f651b8942efaf4861f33f5f694e46cbe8e76638ba5595a687d` |
| Ready | `a1933f5472586cdaeb2249e4f69d37620fdb78a3f92921cb35bfa9028f6e9b0c` |
| Release | `5fdf4a9a1ef9a4e0925cc59ab89f0bc903c83e50c907ac79b8b4e777e8684840` |

The smoke root contains no ledger, exploration manifest, or trace. The AI
marker remained at 15,255 lines with SHA-256
`88db1899d2b442c90380f74aefcf10eab21cc9e91c917295d8c0f3d02da67a76`.
Checkpoint and exploration inventories were unchanged. CommunicationMod config
was restored byte-for-byte with SHA-256
`374806e6386940a5945ffd03411b526d6a21c002b938bb4db253780f787b8e9a`.
No smoke process remained. Two earlier orchestration attempts were excluded
from acceptance and cleaned up before this passing run.

## Historical Artifact Compatibility

The standalone verifier replayed the immutable root
`D:\SteamLibrary\steamapps\common\SlayTheSpire\noncombat_outcome_evidence_expansion_20260715`
with exit code 0 and 534 independent checks.

| Item | Value |
| --- | --- |
| Closeout mode | `integrity_stop` |
| Registration hash | `adf850f96537f01ae29f99d45a56c1d9ffcddecc33665e4c76680515ca6631c2` |
| Run-lock hash | `b6c1a48dfb0c3ba479fe58d4c7d7d280821dd065dc4f9afacdd5ba39fadfd27f` |
| Final ledger record hash | `bcc971070a7b3a78fedab01b7b6c8f998e8648cb9a97ebba0ca0b9d724e868cf` |
| Closeout hash | `9aec815b0e5812eedd093a49f325a566260b459df752f5a88e39fca158483252` |
| Root inventory | 59 files, `84acbb819b90761cd532a5b6bbf158e5a518141cf51fe39dbe863d0ff9d0c2e3` |

All key file hashes remained unchanged and every forbidden normal pool/OPE
artifact remained absent.

## Remaining Limits

- A process can still fail in the final instructions between a guard and the
  next durable file. The protocol detects this on the current or next command;
  it cannot provide a multi-file filesystem transaction.
- The parent can record a cleanup failure but cannot guarantee termination when
  the operating system refuses both terminate and kill.
- Offline evidence proves canonical record bindings and positive recorded PID,
  not historical PID liveness or an additional child acknowledgment after
  release consumption.
- Historical v1 artifacts remain verifiable but are not launchable. Any future
  study requires a separately reviewed v2 registration and a new artifact root.

The authority boundary remains closed: every historical blocked-study authority
gate is false, and no result in this report changes that status.
