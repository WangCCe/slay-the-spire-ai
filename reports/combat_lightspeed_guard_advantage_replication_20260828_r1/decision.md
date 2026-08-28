# Guard-Advantage Replication Decision

## Decision

Close the raw-bootstrap three-step recipe without an optimizer, seed, or
threshold sweep. The earlier small-cohort reward signal did not replicate at
twice the training and evaluation cohort size.

## Fixed Gate

| Criterion | Required | Observed | Result |
|---|---:|---:|---|
| Candidate-only victories vs control-only | at least equal | 21 vs 38 | fail |
| Mean reward delta | greater than 0 | -0.5923 | fail |
| Mean player HP delta | at least 0 | -0.4479 | fail |
| Excluded nonterminal profiles | 0 | 0 | pass |

The run completed 8,192 registered training profiles, 102,358 accepted source
transitions, 256 optimizer updates, and 1,719 terminal paired evaluation
profiles. The candidate parameter L2 delta was 1.3846, so the no-go is not an
unchanged-model or infrastructure result.

## Comparison

The preceding raw-control smoke reported 14 candidate-only victories against
9 control-only victories and a +0.1495 mean reward delta on 853 paired
profiles, although its HP delta was already slightly negative. The larger
fresh replication reverses both victory and reward signals. It therefore does
not support another live candidate or a same-recipe scale-up.

## Next Training Direction

The next materially different recipe should train on explicit paired action
advantage over the guarded baseline:

1. At supported LightSTS states, clone one common environment for the deployed
   guard action and each eligible alternative action.
2. Continue every branch with the same frozen guarded policy and compute a
   fixed-horizon or terminal return delta relative to the guard branch.
3. Train an abstaining residual only on repeatable positive-advantage labels;
   preserve the guarded action elsewhere.
4. Require fresh paired simulator improvement before collecting another live
   replay or running a game gate.

This report grants no gameplay, live transfer, qualification, or promotion
authority. Production r16 remains unchanged.
