## Context

The frozen `noncombat-outcome-evidence-expansion-20260715` study stopped with `terminal_slot_structure_invalid_14` after the host reboot interrupted slot 13 and the next CommunicationMod process never delivered game state. Its `integrity_stop` finalizer correctly wrote only a blocked claim and closeout, but the independent verifier currently rejects `global_stop` inside ledger parsing before it reads the claim. The result is deterministic and fail-closed, yet cannot pass its own independent verification contract.

The runner has a separate ordering problem. `execute_registered_slot` captures the marker boundary and appends `slot_started` before calling the real `main.py` child. A child that never receives CommunicationMod state therefore consumes a registered slot and later becomes an invalid zero-evidence terminal. Future collection needs proof from the actual child process, not from a different probe, before the ledger claims the slot.

CommunicationMod launches the study wrapper and connects it to stdin/stdout. The wrapper then launches the registered `main.py` command with inherited streams. `main.py` can create and signal its coordinator before loading the RL agent, consume one state with callbacks disabled, and retain that state for normal `play_one_game` startup. This provides a narrow place to gate the real child without changing the Java mod or proxying its protocol.

## Goals / Non-Goals

**Goals:**

- Independently replay both normal and blocked registered closeouts from frozen artifacts.
- Make branch selection derive from the validated ledger and claim rather than a report status, CLI flag, or artifact presence guess.
- Require the actual registered child to receive one parseable CommunicationMod state before `slot_started`, exploration initialization, any gameplay callback, or any attributable marker growth.
- Preserve launch-at-most-once and fail-closed accounting across timeout, early exit, malformed readiness, parent failure, and reboot boundaries.
- Keep ordinary gameplay inert when the explicit study-handshake environment is absent.
- Preserve read-only verification of the 2026-07-15 v1 artifact while requiring a handshake contract for every future launchable registration.

**Non-Goals:**

- Do not resume, repair, extend, replace, or pool the blocked 2026-07-15 study.
- Do not create or execute a fresh registration in this change.
- Do not change exploration rates, OPE estimators, evidence thresholds, gameplay policy, rewards, RL state/action spaces, training, or promotion gates.
- Do not change CommunicationMod Java code or introduce a generic stdin/stdout proxy.

## Decisions

### 1. Parse the ledger once, then select an independently verified closeout branch

`_verify_ledger` will validate the append-only chain, ordering, marker arithmetic, active-slot state, and global-stop cardinality without assuming a normal closeout. It will return the terminal prefix plus optional global stop. `_verify_claim` will return the validated claim rather than only incrementing checks.

The top-level verifier will then enforce exactly one branch:

- No global stop requires 24 terminal slots, claim mode `complete`, every normal pool/OPE artifact, and the existing normal replay unchanged.
- A global stop requires claim mode `integrity_stop`, no active slot, a valid terminal prefix followed only by registered unlaunched slots, and the blocked branch.

The blocked branch will independently reconstruct the expected slot table, evidence-gate blockers, null source bindings, all-false authority gates, limitations, closeout hash, and Markdown rendering. It will require the registered pool, target, readiness, estimate, bootstrap, influence, and comparison outputs to be absent. It will not import the finalizer or trust the closeout's own status.

Alternative considered: make the existing normal assertions conditional in place and continue loading normal artifacts. Rejected because missing artifacts are required behavior for an integrity stop and should be a separate, auditable path.

### 2. Use an attempt/ready/release handshake with the real gameplay child

Future registrations will fix a handshake protocol version, a 30-second child readiness deadline, a 10-second release deadline, and deterministic per-slot attempt/ready/release paths. The parent will derive a slot token from the registration hash, run-lock hash, slot number, session ID, and config hash, then pass the binding through explicit environment variables.

The sequence is:

1. The parent validates the run lock and next slot, requires all handshake and gameplay output paths to be absent, and captures the preclaim AI marker count.
2. The parent atomically writes a canonical attempt record before `Popen`. Once that record exists, no process for the slot may be retried under the registration.
3. The parent starts the exact registered child with `subprocess.Popen`, inherited CommunicationMod streams, and the handshake binding. The ledger still shows the slot as unlaunched.
4. Before exploration runtime or agent initialization, the child creates and signals the coordinator, starts its input reader, and polls for one parseable CommunicationMod state with callbacks disabled. It emits no gameplay command.
5. The child atomically writes a canonical ready record bound to the study, run lock, slot, token, attempt hash, and child PID, then waits for release until the fixed deadline.
6. The parent verifies the ready record and live PID, requires the marker count and gameplay output absence to remain unchanged, appends `slot_started` with the original marker boundary, and atomically publishes the bound release record.
7. The child validates release, initializes exploration and the agent, registers callbacks, and continues with the already received state. Normal terminal accounting is unchanged.

Readiness or release timeout, early child exit, duplicate artifacts, malformed JSON, binding mismatch, marker growth, or premature manifest/trace creation will terminate the child and append one global stop while the slot remains unlaunched. If the parent or host dies after publishing the attempt but before recording that stop, the next command treats the orphaned attempt as the deterministic global-stop trigger and never launches another child. If the parent fails after `slot_started` but before release, ordinary active-slot recovery consumes that slot as interrupted and the study stops; a claimed slot is never rolled back to unlaunched.

Alternative considered: run a separate lightweight preflight process and then start `main.py`. Rejected because it proves a different process/configuration and creates a drift window. Alternative considered: have the wrapper consume and proxy the first stdin message. Rejected because bidirectional Windows pipe relaying adds protocol and shutdown risk outside the narrow study need.

### 3. Keep handshake behavior in a small shared module and keep normal startup inert

A focused module will own environment parsing, canonical attempt/ready/release schemas, atomic publication, binding validation, and child wait logic. `main.py` will call it only when the handshake environment is present. The runner will own process lifecycle and ledger ordering. This avoids embedding study JSON rules throughout coordinator or gameplay code.

Normal startup without the environment keeps the current coordinator, exploration runtime, and agent ordering. The explicit handshake path may start the deferred combat-RL stdin reader before agent loading because it must receive the initial state; it must not register callbacks until release.

### 4. Version future registration semantics without rewriting historical evidence

The registration model will support legacy v1 for read-only loading and verification. New registration generation will emit v2 with the handshake contract and hash-bound handshake implementation path. `start` and `run-next` will reject launchable v1 registrations after this change; the frozen v1 report and external artifact bytes remain unchanged.

No migration rewrites existing registration, run-lock, ledger, claim, closeout, or external artifact files. The old blocked closeout is the compatibility fixture, not input to a new pool.

### 5. Verification is regression-first and stops before live collection

Tests will first encode the observed blocked artifact shape and the preclaim ordering failure. Focused coverage will include normal and blocked verifier branches, every blocked-closeout binding and forbidden-artifact tamper, attempt/ready/release schema tampering, orphaned attempts, timeout and early exit before claim, success ordering, failure after claim, v1 launch rejection, v1 read-only verification, and no-environment startup.

After focused and full Windows pytest, the standalone CLI will verify a read-only copy or the immutable external 2026-07-15 blocked artifact. The change closes with strict OpenSpec validation, byte and whitespace checks, and independent review. A separate approved change must create any fresh registration.

## Risks / Trade-offs

- [The child receives a state before callbacks exist] -> Use `perform_callbacks=False`, retain `last_game_state`, and add a regression proving normal startup consumes that retained state exactly once after release.
- [Parent or host fails between claim and release] -> Never unclaim the slot; recover it as interrupted and globally stop, preserving launch-at-most-once.
- [The parent dies after starting a child but before ledger claim] -> Publish an exclusive attempt record before `Popen`; recovery converts any orphaned attempt into a global stop and never retries the slot.
- [A stale attempt, ready, or release file is mistaken for the current child] -> Require exclusive creation, deterministic slot token, exact attempt/run-lock/config binding, and matching live child PID.
- [Handshake timeout is too short on a slow machine] -> Signal ready before RL loading and fix 30-second readiness plus 10-second release deadlines in registration so they cannot be adapted after outcomes; timeout blocks the registration rather than consuming a slot.
- [Verifier branching could weaken normal checks] -> Keep the current normal path intact behind explicit normal invariants and add regression snapshots for its check outputs.
- [Supporting v1 broadens parser complexity] -> Limit v1 to read-only verification and reject all future v1 launches.

## Migration Plan

1. Keep the 2026-07-15 artifact root closed and immutable.
2. Add blocked verifier regressions and implement the independent branch; prove the historical blocked artifact passes without study imports.
3. Add handshake schemas and child gate regressions, then change runner ordering and `main.py` startup only for explicit study environments.
4. Add registration v2 generation and v1 launch refusal while preserving v1 verification.
5. Run focused and full Windows pytest, strict OpenSpec validation, static/byte checks, and independent review; commit a no-live-collection report.
6. In a later approved change, preregister a new artifact root and run a no-game handshake smoke test before any bounded collection.

Rollback is a code revert plus removal of the explicit handshake environment from CommunicationMod. Ordinary bounded `--eval` remains the operational fallback; no evidence or checkpoint migration is required.

## Open Questions

None. The old study remains blocked, the initial state is used only as communication proof until release, and every handshake failure stops rather than retries the registration.
