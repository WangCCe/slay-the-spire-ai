# Full-return End Turn trust candidate r13

## Decision

Retain r13 as a behavior-safe offline negative, but do not promote it. It passed
fresh replay confirmation and then tied production r8 on all 20 matched live
floor outcomes. Production remains on r8.

The candidate was fitted on consumed r7 replay with the r12 full-combat-return
objective, eight full-dataset SGD steps, learning rate `0.0002`, TD weight
`0.2`, parent Q anchor weight `1.0`, and interpolation `alpha=0.5`. The new
term penalizes erosion of the promoted parent's non-End-over-End margin only
when energy is positive and End Turn is a legal alternative.

## Development result

| Replay | Parent full-return | Candidate | Parent one-step | Candidate | Agreement | Off-target | Positive-energy End Turn |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| r6 | 46.5518 | 46.5203 | 4.1432 | 4.1210 | 99.3880% | 0.4765% | 1,975 -> 1,961 |
| r8 | 50.6912 | 50.6615 | 4.3358 | 4.3160 | 99.6986% | 0.2330% | 1,643 -> 1,637 |
| r9 | 48.7806 | 48.7508 | 4.2415 | 4.2196 | 99.5379% | 0.5424% | 1,699 -> 1,693 |

Every replay passes both loss improvements, `>=99%` parent agreement, `<=1%`
off-target disagreement, and a positive-energy End Turn increase of at most
one. The selected candidate has relative L2 movement `7.8277e-6` from r8.

## Selection

The fixed development sweep used preservation weights
`[0, 0.25, 0.5, 1, 2, 4]`. Weight zero exactly reproduced r12 and failed r9
with `1.0848%` off-target disagreement and eight additional positive-energy
End Turns. Every positive weight passed all three development replays. The
smallest passing positive weight, `0.25`, was selected to apply the least
additional constraint while closing the observed boundary failure.

The frozen checkpoint is
`rl_combat_model_return_end_turn_trust_candidate.pth`, SHA-256
`b05bbb904bee075628691565de98fbdc119bbae0fc2cc2e41e55acd5084bafe7`.

## Fresh r10 confirmation

R10 contributed 3,081 complete, zero-update production-r8 transitions. The
candidate improved full-combat-return SmoothL1 from `54.7217827` to
`54.7010956` and one-step SmoothL1 from `4.4317813` to `4.4114928`. Parent
action agreement was `99.6430%`, off-target disagreement was `0.5305%`, and
positive-energy End Turn count fell from 1,624 to 1,621. Every registered
condition passed.

The raw confirmation is preserved unchanged. Its descriptive `source_commit`
argument used the correct registered prefix but an incorrect expanded suffix;
`r10_fresh_confirmation_provenance_erratum.json` binds the actual full commit.
No metric, checkpoint, replay, threshold, or evaluation execution is affected.

## Matched live gate

Candidate and parent produced the same 20-floor vector, 439 total floors, ten
Act 2 entries, four Act 2 boss reaches, zero Act 3 entries, and zero victories.
All 20 floor pairs tied and both runtime bundles were clean. The preregistered
non-tie requirement failed, so r13 has no observable live benefit.

## Next step

Do not repeat this cohort. Keep the End Turn trust term and test a larger
effective full-return step using consumed replay only. Require r6, r8, r9, and
r10 to pass the same loss and behavior guards before collecting another fresh
holdout.
