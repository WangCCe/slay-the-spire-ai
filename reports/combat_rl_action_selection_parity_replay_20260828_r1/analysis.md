# Combat RL Action-Selection Parity Replay R1

## Result

The registered ten-game collection completed all seeds in order and retained
2,109 real combat transitions. No optimizer update occurred: online and target
weights remain byte-equivalent to production r16, optimizer state is empty,
and `learning_starts=100000` remained above the replay count.

The action-selection parity fix passes its fresh criterion. All 466 direct
unmarked actions equal the frozen production-r16 eval-mode greedy action. The
previous train-mode cohort had 44 disagreements among 239 direct rows. The new
cohort preserves 1,643 legal override rows, so parity was not obtained by
disabling guard or takeover provenance.

## Evidence Binding

The batch crossed two 10 MB log rotations. The retained `.2`, `.1`, and current
debug logs form a continuous sequence over all ten seeds. They contain 1,009 RL
proposals, no traceback, no RL action failure, and one natural max-games exit.
The replay provenance reconciles exactly:

- `1,643 = 1,100 no-proposal actions + 543 changed proposals`
- `466 = 1,009 proposals - 543 changed proposals`

The decision trace has 2,109 joinable combat actions. Every row matches replay
floor and action family. Inventory identity also joins one-to-one with zero
potion or relic mismatch and zero unresolved occupied object. There are no
cross-floor nonterminal successors.

## Training Decision

Approve this checkpoint as training-only input for one separately registered
provenance-aware successor. This is not policy-quality evidence: the ten runs
had no victory, and these seeds must not be reused for candidate selection,
fresh confirmation, or promotion.

The next change should preregister a bounded optimizer budget and a parent
anchor that uses frozen r16 greedy labels on direct rows and executed-action
labels only on the 1,643 provenance overrides. Freeze one materially distinct
candidate, then collect a separate unused fresh holdout before any live gate.
