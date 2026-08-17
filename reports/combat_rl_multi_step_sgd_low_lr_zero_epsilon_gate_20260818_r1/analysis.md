# Low-rate multi-step SGD matched live gate

## Decision

Retain the promoted r8 parent. The frozen r10 candidate did not satisfy the
preregistered requirement for an observable matched-seed benefit.

| Metric | Candidate | Parent |
| --- | ---: | ---: |
| Games | 20 | 20 |
| Victories | 0 | 0 |
| Total floors | 468 | 468 |
| Mean floor | 23.40 | 23.40 |
| Median floor | 22 | 22 |
| Act 2 entered | 11 | 11 |
| Act 2 boss reached | 7 | 7 |
| Act 3 entered | 0 | 0 |

All twenty floor pairs tied. The seed, non-combat path, and final `killed_by`
value matched in every pair. The candidate therefore recorded zero paired
wins, zero paired losses, and a summed floor delta of zero.

## Integrity

Both arms completed all twenty games naturally. Candidate and parent decision
traces contain 7,076 and 7,065 rows, all with source `combat_rl`. The bytes
appended to `communication_mod_errors.log` contained no traceback, critical
error, or exception. No training or expert actions were enabled.

CommunicationMod rewrote only the first properties comment to its timestamp
when each arm launched; the registered command and arguments were unchanged.
Production was restored to the promoted r8 configuration with SHA-256
`f87804b2768b8ff53d0760fbfd267c5282afed21081ea888c336e0263041efcb`.

## Interpretation

The r10 update improved SmoothL1 on both the r6 development replay and the
one-use r7 holdout, but its `1.3652e-6` relative parameter movement produced no
observable live behavior change in forty matched games. This is useful negative
evidence: stability is no longer the limiting issue; the parent anchor and
smallest-passing interpolation rule make the policy step too conservative.

Do not promote r10 and do not run another live gate for the same construction.
The next combat-RL experiment should target a materially larger but bounded
policy update, use consumed r7 data for fitting or development, and reserve a
new fresh production-policy replay for confirmation.
