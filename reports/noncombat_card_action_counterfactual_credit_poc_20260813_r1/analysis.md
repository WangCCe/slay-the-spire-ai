# Card Action Counterfactual Credit POC

## Result

Verdict: `card_action_counterfactual_credit_viable` for a later bounded
training-integration experiment. This is a signal-availability result, not a
policy-quality, qualification, or promotion claim.

- 15 complete card-reward source states across consumed development seeds
  `1000..1007`
- 61 charged action continuations, including one exact repeat branch
- 11 source states with nonzero terminal-return spread
- 7 source states with both nonzero spread and a unique best action
- mean spread `0.1356725`, median `0.0701754`, maximum `0.5087719`
- exact fixed-branch replay passed
- production checkpoint and CommunicationMod isolation passed
- charged runtime `199.563` seconds

The fixed gates required at least eight complete source states and four
informative unique-best states, so the POC passed without changing any
preregistered threshold. The 64-branch boundary stopped before a partial 16th
source state; 61 branches had already produced 15 complete comparable states.

## Interpretation

All 60 non-repeat action branches ended in `player_loss`; no branch produced a
terminal victory. The observed action credit therefore comes entirely from the
formal floor-progress shaping channel. Six of seven unique best actions took a
card and one skipped. Four additional states had nonzero spread but tied best
actions, while four states had zero spread.

This evidence is strong enough to test whether direct counterfactual ranking
reduces trajectory-level gradient variance on consumed support. It is not
strong enough to start formal non-combat RL, use fresh seeds, or claim that the
counterfactual ranking improves victory probability. The next experiment
should fit on one consumed-seed partition and compare held-out counterfactual
top-action regret/ranking on a disjoint consumed-seed partition.

## Verification

Focused evaluator and runner tests: `15 passed in 4.32s`. Python compilation and
OpenSpec strict validation passed. The full gameplay test gate was intentionally
not run because this change adds isolated analysis-only code, does not alter the
agent or simulator, and the project time allocation reserves long full-suite
runs for shared or live-behavior changes.
