# Event Option Counterfactual Outcomes Closeout

## Verdict

`event_option_counterfactual_signal_viable_for_learning_proposal`

The fixed `94000..94063` cohort produced enough complete, diverse, and
deterministically replayable action-level outcomes to justify a separate event
learning proposal. This result does not establish policy quality and does not
authorize promotion or gameplay use.

## Evidence

- 122 complete multi-option event sources from 64 seeds
- 287 forced option branches under fresh frozen Current-policy continuation
- 49 informative sources across 21 distinct event ids
- 16 of 16 exact branch replays passed
- 3 sources were censored at the registered Courier restock boundary
- Mean return spread was `0.089445`; maximum spread was `2.315789`
- Current selected an outcome-maximizing option, including ties, on 98 of 122
  sources (`80.33%`); its mean source regret was `0.032499`

The largest spread was a valid terminal outcome difference for World of Goop:
one branch reached floor 51 and victory while the other ended on floor 33 in a
loss. Informative outcomes appeared across 12 event names, rather than being
confined to that outlier.

## Integrity

- All four manifest-bound artifacts matched their recorded byte sizes and
  SHA-256 digests.
- Source rows cover seeds `94000..94063`.
- The collector did not launch gameplay or CommunicationMod, fit a model, or
  access a production checkpoint.
- Focused event and shared-continuation tests passed: `14 passed in 7.82s`.
- Strict OpenSpec validation passed.

## Next Step

Create a separate, preregistered event-option learning experiment with disjoint
train and development seeds. Compare a fitted ranker with Current on mean
regret, tail regret, unique-best accuracy, and per-event support. Treat the
development cohort as single-use and stop on any fixed gate failure.
