# Combat RL Candidate Callability Audit

## Decision

Record candidate-callability provenance before implementing a residual or
separate Q head. The next fresh replay must distinguish direct unchanged RL
proposals, changed same-state RL proposals, and actions emitted while no RL
proposal exists. Legacy rows with no such identity must remain explicit and
ineligible for callability-filtered fitting.

## Evidence

The committed replay has 2,091 transitions but only 928 RL proposals. Of those
candidate-callable states, 391 executed the unchanged proposal and 537 executed
a guard replacement. The other 1,163 rows, or 55.6% of the corpus, were emitted
while the outer wrapper had already bypassed RL for fallback-turn takeover.

The current replay stores only `anchor_to_executed_action`. It therefore merges
the 537 changed proposals with all 1,163 no-proposal actions. No-proposal rows
make up 68.4% of the merged override stratum, so even the balanced objective's
override half is dominated by states where a deployed candidate is never
called.

The control-flow evidence is direct: the active takeover branch occurs before
the RL call in `CombatRLAgent`, and `RLAgentV2.commit_executed_action()` creates
a new pending transition marked only as an override when no proposal exists.
Replay schema v2 persists that boolean but no proposal identity.

## Consequence

A residual/head POC on the current tensors would not isolate override learning;
it would still optimize mostly toward fallback actions on candidate-unreachable
states. This is a stronger and earlier problem than shared-network parameter
interference.

The next implementation should persist an exact proposed action identity with
explicit no-proposal and legacy-unknown sentinels. A future candidate fit may
use only direct and changed-proposal rows. No-proposal takeover rows remain
useful for wrapper diagnostics and outcome accounting, but not for updating the
candidate policy. After a fresh replay proves complete provenance, rerun one
fixed callability-filtered objective before deciding whether a residual head is
still necessary.
