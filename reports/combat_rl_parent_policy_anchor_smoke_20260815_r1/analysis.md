# Combat RL parent-policy anchor smoke R1

## Decision

**Approve one fresh matched zero-epsilon live gate against the promoted parent. Do not promote from replay or training-cohort evidence alone.**

## Anchor result

The fixed `0.25` parent-policy anchor completed exactly 20 games, accepted 4,040 transitions, and performed 1,010 optimizer updates. The final checkpoint is finite, stores the configured weight, and its frozen anchor state is tensor-for-tensor identical to the promoted parent's online policy.

On the successor replay, SmoothL1 decreased from `3.4031` for the parent to `3.1150` for the successor. Parent/successor greedy agreement is `81.13%`, clearing the preregistered `72%` threshold and improving by `17.70` percentage points over the rejected unanchored broad successor's `63.43%`. The last stored anchor loss is finite and positive at `0.5456`; 34 periodic samples range from `0.4694` to `0.7981`.

## Training integrity

The training seed order exactly matches the rejected unanchored broad continuation. The batch logged 1,950 selected expert actions and 815 mix skips, with zero masked, unencodable, failed, or replay-rejected transitions. All executed replay actions remain valid under their stored masks.

The training cohort produced 499 floors, 13 Act 2 entries, five Act 2 boss reaches, one Act 3 entry, and no victory. These outcomes have no evaluation authority because training used expert mixing and exploration.

CommunicationMod log growth was the expected 1,013-byte launch record. The promoted parent production configuration was restored and all game and Python processes were closed before offline analysis.
