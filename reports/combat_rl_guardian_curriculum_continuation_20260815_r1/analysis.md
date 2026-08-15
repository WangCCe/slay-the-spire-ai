# Combat RL Guardian curriculum continuation R1

## Decision

**Approve one fresh matched zero-epsilon live gate against the currently promoted parent. Do not promote this successor from training-cohort results.**

## Training result

The 12-game continuation accepted 1,905 transitions and completed 476 optimizer updates. The final checkpoint is finite and retains 4,096 replay transitions from 6,001 source transitions.

On the successor replay, SmoothL1 decreased from `3.4014` for the parent to `2.9689` for the successor. Median absolute TD error decreased from `1.3325` to `1.1923`, and p95 decreased from `9.8514` to `8.5589`. The p05 Q margin increased from `0.0478` to `0.0544`, while the median margin decreased from `0.9404` to `0.8739`. All executed actions remained valid under their stored masks.

The successor changed materially enough to require live evaluation: parent/successor greedy agreement is `68.9%`, with whole-model relative L2 drift of `1.30%` and advantage-stream drift of `7.66%`.

## Curriculum signal

All 12 seeds were previously consumed Guardian failures and therefore have no evaluation authority. The continuation passed Guardian on four seeds and reached the Act 2 boss in all four; eight seeds still died to Guardian. In the eight-seed subset from the latest matched gate, three passed Guardian during training.

The full batch logged 1,119 selected expert actions and 477 mix skips, a `70.1%` successful expert share. It recorded zero masked, unencodable, failed, or rejected expert transitions.

## Integrity

The batch completed exactly 12 games. CommunicationMod error growth was the expected 974-byte launch message, the explicitly promoted parent evaluation configuration was restored, and all game/Python processes were closed.

The successor remains an offline candidate only. A future gate must use a newly registered seed pool with no overlap with the curriculum or earlier combat gates.
