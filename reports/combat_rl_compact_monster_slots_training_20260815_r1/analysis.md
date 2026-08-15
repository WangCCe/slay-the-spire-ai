# Combat RL compact monster-slot training R1

## Decision

**Approve one fresh matched zero-epsilon live gate against the frozen entry checkpoint. Do not promote this candidate without that gate.**

## Training result

The fresh 25-game batch accepted 5,167 transitions and completed 660 optimizer updates after crossing the replay learning threshold. The final checkpoint is finite and contains 4,096 retained transitions from 6,732 source transitions.

On the candidate replay, SmoothL1 decreased from `4.2782` for the entry model to `3.1497` for the candidate. Median absolute TD error decreased from `1.4997` to `1.1883`, and p95 decreased from `11.2117` to `9.7642`. All executed actions were valid under their stored masks.

The candidate changed materially: whole-model relative L2 drift is `2.74%`, and advantage-stream drift is `23.06%`. Replay fit alone is therefore insufficient for promotion.

## Live outcomes

The 25 training games produced 608 total floors, mean `24.32`, median `24`, 17 Act 2 entries, eight Act 2 boss reaches, no Act 3 entry, and no victory. This is stronger than the previous expert-dominant training cohort, but the seeds were not matched, so it is only a coverage signal.

The retained final log window contains 522 selected and 228 skipped expert decisions, for a `69.6%` successful expert share, with zero masked, failed, or unencodable expert actions. Earlier full-batch counts were lost to normal log rotation; the targeted two-seed smoke separately proved raw target index 6 behavior.

## Integrity

The batch completed exactly 25 games without CommunicationMod errors beyond expected launch output. The original configuration was restored and all game/Python processes were closed.
