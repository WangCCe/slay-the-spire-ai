# Weight-one parent-policy anchor training

## Decision

The controlled `parent_policy_anchor_weight=1.0` successor passes the preregistered offline gate and may proceed to a fresh matched candidate-versus-parent evaluation. This training cohort has no promotion authority.

## Evidence

- The bounded batch completed exactly 20 games and produced `ep60_steps22590` with SHA-256 `b8916452702411dcea2bca7bbf996bc349a9060f162256af7d4d597cafce5986`.
- On the successor replay, SmoothL1 improved from `4.061614` for the promoted parent to `3.428365` for the successor.
- Parent greedy-action agreement is `88.135%`, above the preregistered `88%` minimum.
- The frozen anchor exactly matches the promoted parent online policy, checkpoint tensors are finite, and all executed replay actions are valid under their masks.
- The batch completed naturally with zero CommunicationMod error-log growth. Retained logs contain no expert adapter or transition failures.

## Coverage limitation

The five-file rotating debug log retained records from `19:10:11` onward, so approximately the first eight minutes are no longer directly searchable. The retained interval covers 1,875 expert selections, 804 expert-mix skips, and 33 anchor updates; the missing interval is disclosed rather than reconstructed. Full-batch integrity is additionally supported by natural completion, unchanged error-log size, valid replay actions, and a finite checkpoint.

## Outcome context

Training outcomes were 499 total floors over 20 games, with 11 Act 2 entries, 6 Act 2 boss reaches, 2 Act 3 entries, and no victories. These consumed-seed outcomes are diagnostic only and are not used for promotion.

## Next step

Run one preregistered 20-seed fresh matched gate at epsilon zero for the weight-one successor and the promoted parent. Retain the parent unless the candidate wins more seed pairs and matches or exceeds the parent total floors under the fixed gate rules.
