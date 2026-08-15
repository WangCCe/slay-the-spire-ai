# Combat RL parent-policy anchor zero-epsilon gate R1

## Decision

**Reject the anchored candidate and retain the promoted parent. Do not start the parent arm or retry this gate.**

## Integrity failure

The candidate arm completed eight of 20 registered games, then entered a live policy nontermination on seed `0TP19MYO9CPA8`. At floor 19 against Spheric Guardian, protocol state updates continued and `rl_failure_count` remained zero, but the policy repeatedly alternated `ENERGY_GUARD` fallback turn takeover actions without making combat progress.

The screenshot at turn 189 records 651 enemy block. A fixed short observation window showed the loop continue through turn 232, and the final log reached turn 249 without producing a run record. This is candidate behavior, not a CommunicationMod stall.

## Gate handling

The preregistered gate required both arms to have zero integrity warnings and all conditions to pass. Candidate integrity was already false, so the candidate arm was stopped without retry and the parent arm was not started. The eight completed candidate runs produced 180 floors but have no matched comparison authority.

The promoted parent production configuration was restored, and all game and Python processes were closed. The next evidence task is a narrow regression and policy-safety fix for deterministic no-progress combat loops before any further anchored candidate training or qualification.
