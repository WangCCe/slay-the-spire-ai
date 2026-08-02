# Baseline Warm-Start Validation Failure Audit

## Decision

The valid negative warm-start result is primarily explained by insufficient
teacher-state competence on real multi-candidate decisions, not by a late
rollout-only failure. Exposure shift may amplify the deficit after divergence,
but the fixed artifacts cannot isolate that effect and do not justify another
run.

Formal non-combat RL remains blocked. The next justified change is a bounded,
separately reviewed structured baseline-ranker POC. It should improve
candidate-relative, category-aware representation and measure nontrivial-choice
fit before considering data aggregation or RL.

## Fixed evidence and method

This audit used only the completed study artifacts:

- registration SHA-256:
  `2815274e61c7d4ad8e553190ca234d6303457d9543cd63def541637729340a7a`;
- demonstration SHA-256:
  `6b549ad2f54cea6e08f4399e9ec5cda12d20b3bb3f18fa5349cdb544d48050c6`;
- trajectory SHA-256:
  `c9d320a213e49f1f30760104e5c0ae7c0a06d7fabd72225bf7de077b51450bc8`;
- frozen model SHA-256:
  `a356ac955e8eff419ce9848c6e26cd0992f174656d4f5f8c4a2414659967215a`.

For each validation seed, candidate and SimpleAgent selected-action sequences
were aligned until their first unequal action. The preceding action prefix is
identical, so the joined native demonstration is the same policy state. The
audit verified that the candidate action equals the published frozen-model
prediction and the SimpleAgent action equals the row's teacher target.

The terminal floor difference is descriptive for the entire policy branch
after that first divergence. It is not an isolated causal value for the first
action because both policies make additional decisions on different successor
states.

## First divergences

| Seed | Decision | State floor | Category | Candidate | SimpleAgent | Teacher p | Floors C/N | Gap |
| ---: | ---: | ---: | --- | --- | --- | ---: | ---: | ---: |
| 5000 | 7 | 3 | route | `?@2,3` | `M@0,3` | 0.461585 | 8 / 16 | -8 |
| 5001 | 1 | 1 | card_reward | Dropkick | Seeing Red | 0.269298 | 7 / 8 | -1 |
| 5002 | 0 | 0 | card_reward | Forethought | Discovery | 0.263496 | 51 / 21 | +30 |
| 5003 | 3 | 2 | card_reward | Inflame | Bloodletting | 0.257169 | 11 / 24 | -13 |
| 5004 | 1 | 0 | route | `M@1,0` | `M@2,0` | 0.241165 | 13 / 28 | -15 |
| 5005 | 0 | 0 | card_reward | Iron Wave | Clothesline | 0.248855 | 6 / 16 | -10 |
| 5006 | 6 | 3 | route | `?@6,3` | `$@4,3` | 0.329149 | 33 / 33 | 0 |
| 5007 | 2 | 1 | route | `?@0,1` | `M@2,1` | 0.453903 | 7 / 16 | -9 |
| 5008 | 6 | 3 | event | Woman in Blue option 1 | option 0 | 0.234568 | 16 / 24 | -8 |
| 5009 | 2 | 1 | card_reward | Body Slam | Infernal Blade | 0.259282 | 16 / 51 | -35 |
| 5010 | 0 | 0 | card_reward | Trip | Flash of Steel | 0.283868 | 23 / 33 | -10 |
| 5011 | 0 | 0 | route | `M@4,0` | `M@2,0` | 0.336045 | 39 / 33 | +6 |
| 5012 | 0 | 0 | route | `M@4,0` | `M@2,0` | 0.335387 | 33 / 16 | +17 |
| 5013 | 0 | 0 | route | `M@1,0` | `M@2,0` | 0.241649 | 23 / 16 | +7 |
| 5014 | 2 | 1 | card_reward | Metallicize | Evolve | 0.254402 | 28 / 33 | -5 |
| 5015 | 0 | 0 | route | `M@1,0` | `M@5,0` | 0.250735 | 6 / 27 | -21 |

Eight first divergences were route decisions, seven card rewards, and one
event; none was a shop decision. Thirteen occurred within the first five target
decisions, twelve by floor 1, and all by floor 3. The first-divergence teacher
probability had mean 0.2950, median 0.2614, and range 0.2346 to 0.4616.

Candidate floor was lower on 11 seeds, higher on four, and tied on one. The
median gap was -8 floors. Card-reward first divergences averaged -6.29 floors;
route averaged -2.88; the single event row was -8. These small category groups
are descriptive and not category-level effect estimates.

## Headline-fit inflation

The published 79.01% validation action agreement includes 234 rows with only
one legal candidate. Those rows are necessarily correct. On the 471 rows that
actually require a choice, agreement is only 68.58%.

| Category | Rows | Singleton share | All agreement | Multi-choice agreement |
| --- | ---: | ---: | ---: | ---: |
| card_reward | 175 | 0.00% | 64.00% | 64.00% |
| event | 69 | 11.59% | 92.75% | 91.80% |
| route | 383 | 55.87% | 84.60% | 65.09% |
| shop | 78 | 15.38% | 73.08% | 68.18% |

Route's headline metric is therefore not evidence of reliable path choice.
More than half of its teacher rows are forced moves, while route accounts for
half of all first divergences.

## Train fit and generalization

Read-only inference of the frozen final model on its existing train
demonstrations produced 84.04% overall and 83.57% macro-category agreement.
Across 870 multi-candidate train rows, agreement was 76.32%, versus 68.58% on
validation.

| Category | Train all | Train multi | Validation all | Validation multi |
| --- | ---: | ---: | ---: | ---: |
| card_reward | 74.17% | 74.17% | 64.00% | 64.00% |
| event | 98.70% | 98.61% | 92.75% | 91.80% |
| route | 87.12% | 70.33% | 84.60% | 65.09% |
| shop | 74.31% | 70.16% | 73.08% | 68.18% |

The fixed ten-epoch training loss decreased monotonically from 1.07635 to
0.99255. This does not authorize extending the observed schedule. It shows
that the registered model was neither a strong train-state imitator nor a
strong fresh-state generalizer, so rollout data aggregation alone is not the
first repair.

## Coverage and representation

No validation source snapshot or full policy view exactly duplicates train,
as expected for fresh seeds. After normalizing away offer/reward slots while
retaining item/event semantics, unseen teacher targets were materially harder:

| Category | Seen target accuracy | Unseen rows | Unseen target accuracy |
| --- | ---: | ---: | ---: |
| card_reward | 66.88% | 15 | 33.33% |
| event | 98.39% | 7 | 42.86% |
| shop | 80.00% | 8 | 12.50% |

However, 13 of 16 first-divergence teacher targets were semantically present in
train. Coverage gaps are real but do not explain the main early-divergence
pattern.

The v1 encoder flattens list-indexed state and candidate JSON, hashes leaves
into 1,024 signed bins, adds shared state and candidate vectors, and feeds one
shared 128-unit ReLU scorer. At first-divergence states, a policy view had a
median 515 leaf tokens but only 407 unique bins, a descriptive median collision
fraction of 20.78%.

More importantly, the representation has no explicit candidate-relative route
reachability summary, permutation-invariant deck/card interaction, or
category-specific head. A start-map choice must infer the selected coordinate's
future path from an indexed flattened map; a card or shop choice must infer
candidate/deck interaction from indexed card rows. The static design and
observed category errors support a structured-feature hypothesis, but they do
not prove which individual feature will recover floor parity.

## Next gate

A separate OpenSpec proposal should define a structured baseline-ranker POC
with these boundaries:

1. Use only already observed train evidence for implementation fit and model
   selection; make no policy-quality claim from that work.
2. Add permutation-invariant state summaries and category-specific,
   candidate-relative features, especially route lookahead and card/deck/shop
   interactions, while preserving the complete action set.
3. Report and threshold multi-candidate agreement separately so forced actions
   cannot satisfy competence gates.
4. Choose schedule and architecture with train-only grouped evaluation, then
   preregister entirely fresh train/validation/final cohorts before native use.
5. Consider DAgger-style candidate-state labeling only if teacher-state
   multi-choice fit becomes credible but independent rollout remains weak.
6. Keep SimpleAgent auxiliary, every downstream authority false, and Current
   and Bottled outside training until their bridges are validated.

No game, native environment, new seed, training update, threshold change, or
live artifact was used by this audit.
