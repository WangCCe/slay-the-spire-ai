# Card Counterfactual Ranking Training R2

## Result

Verdict: `card_counterfactual_ranking_training_not_ready`.

- 30 complete train source states, including 24 informative states
- 16 complete disjoint holdout source states, including 7 informative states
- 185 native action continuations and 32 full-batch optimizer steps
- one preregistered train censor: seed `1014`, Courier restock semantics
- production checkpoint and CommunicationMod isolation passed
- charged runtime `538.172` seconds

Training fit the source partition: pairwise loss fell from `3.003983` to
`0.654573`, train weighted pairwise accuracy rose from `0.4545` to `0.8310`,
and train mean top-action regret fell from `0.07135` to `0.05205`.

The disjoint holdout moved in the wrong direction:

- mean top-action regret: `0.02083` to `0.03618`
- maximum top-action regret: `0.19298` to `0.29825`
- weighted pairwise accuracy: `0.49020` to `0.42484`
- unique-best top-1 accuracy: unchanged at `0.25`
- corrected wrong-to-best flips: `0`

Five held-out greedy actions changed. Four changes occurred on zero-regret tie
states. The only informative change was seed `1021`, where the entry skip action
had regret `0.05263` and training changed it to Carnage with regret `0.29825`.

## Diagnosis

The failure is overfitting, not lack of optimization. Both card heads moved
primarily through their high-capacity hidden matrices:

- family hidden weight L2 `2.1382`; family scorer weight L2 `0.1510`
- conditional hidden weight L2 `2.0509`; conditional scorer weight L2 `0.1703`

The train partition also had denser signal than holdout: 24/30 informative
sources with mean informative spread about `0.17`, versus 7/16 and about `0.11`.
Reducing the number of full-model steps against this exposed holdout would be
post-hoc tuning. The fitted checkpoint remains experiment-local and has no
further-training, evaluation, qualification, promotion, or policy-quality
authority.

## Next Boundary

Treat seeds `1016..1023` as exposed development support. A subsequent proposal
may reconstruct the deterministic train/development datasets and fit only the
two 64-wide scorer layers while freezing both hidden matrices. It must reserve
already-consumed seeds `1024..1031` as a new independent audit and may access
that audit only after fixed development gates pass. The audit split and gates
must be registered before implementation.

## Verification

Focused training and runner tests passed (`12 passed in 16.67s`), followed by
the worker-entry regression suite (`18 passed in 4.71s`). Python compilation
and OpenSpec strict validation passed. The full gameplay suite was not run
because the change is isolated analysis/training code and does not alter live
agent behavior.
