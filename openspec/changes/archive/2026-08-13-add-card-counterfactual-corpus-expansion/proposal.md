## Why

Three card-policy methods gave conflicting development results and none passed
independent audit; the common constraint is only 46 exposed training/development
states plus 15 now-exposed audit states. The next useful investment is a much
larger reusable counterfactual corpus, not another architecture trial on the
same small sample.

## What Changes

- Reserve previously unused seeds `80000..80383` as disjoint train,
  development, and untouched audit cohorts.
- Collect train `80000..80255` and development `80256..80319`, with at most two
  complete card states per seed and four counterfactual continuations per state.
- Persist full canonical state/candidate features and formal action returns for
  later source-only training.
- Reserve but do not access audit `80320..80383` in this change.
- Publish support, censor, return-spread, and card/action coverage diagnostics;
  no model selection or policy-quality claim is made.

## Capabilities

### New Capabilities

- `noncombat-card-counterfactual-corpus-expansion`: Defines the large disjoint
  corpus schedule, native collection limits, canonical dataset publication,
  untouched audit reservation, and no-authority result.

### Modified Capabilities

None.

## Impact

- Adds one bounded native corpus runner and focused tests.
- Executes at most 2,560 action branches, expected to take about two hours on
  the current Windows native simulator.
- Does not start the game/CommunicationMod, train a model, access the reserved
  audit, or modify production checkpoints. Rollback remains r7/native policy.
