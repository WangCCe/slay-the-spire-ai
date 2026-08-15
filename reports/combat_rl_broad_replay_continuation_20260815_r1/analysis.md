# Combat RL broad replay continuation R1

## Decision

**Approve one fresh matched zero-epsilon live gate against the promoted parent. Do not promote from replay or training-cohort evidence alone.**

## Training result

The 20-game broad continuation accepted 3,595 transitions and completed 898 optimizer updates. The final checkpoint is finite and retains 4,096 replay transitions from 7,691 source transitions.

On the successor replay, SmoothL1 decreased from `3.4066` for the parent to `2.9217` for the successor. Median absolute TD error decreased from `1.3324` to `1.1737`, and p95 decreased from `9.9566` to `8.3745`. All executed actions remained valid under their stored masks.

The update is material: parent/successor greedy agreement is `63.4%`, whole-model relative L2 drift is `2.04%`, and advantage-stream drift is `11.38%`. Median Q margin decreased from `0.8853` to `0.6513`, while p05 remained effectively flat. These mixed policy-shape signals require fresh live evidence.

## Training cohort

The consumed 20-seed broad cohort produced 457 floors, 11 Act 2 entries, five Act 2 boss reaches, one Act 3 entry, and no victory. These outcomes have no evaluation authority because training used expert mixing and exploration.

The full batch logged 1,693 selected expert actions and 724 mix skips, a `70.0%` successful expert share. It recorded zero masked, unencodable, failed, or rejected expert transitions.

## Integrity

The batch completed exactly 20 games. CommunicationMod error growth was the expected 978-byte launch message, the promoted parent evaluation configuration was restored, and all game/Python processes were closed.
