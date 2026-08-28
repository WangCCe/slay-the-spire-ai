## Why

The latent-gated live candidate and the larger raw-bootstrap LightSTS
replication both regressed against production r16. Existing recipes either
imitate the deployed guard imperfectly or learn generic TD updates without an
explicit estimate of improvement over the guard action, so another threshold
or optimizer sweep is not justified.

## What Changes

- Add a bounded LightSTS POC that clones one supported combat state into a
  guarded-baseline branch and eligible alternative-action branches.
- Continue every branch with one frozen guarded policy and record paired return
  advantage, support status, action identity, and provenance.
- Fit a development-only abstaining residual on positive-advantage labels and
  evaluate it on a fixed fresh simulator holdout against the guarded baseline.
- Publish explicit coverage, label stability, paired policy metrics, and a
  training go/no-go decision.
- Keep production r16, gameplay routing, CommunicationMod, and production
  checkpoints unchanged.

Live evidence motivating the change is the ten-pair latent-gated matched gate:
the candidate lost two pairs and won none, with 168 total floors versus 184.
The larger fresh LightSTS replication also failed all three policy gates:
candidate-only victories 21 versus 38, mean reward delta -0.5923, and mean HP
delta -0.4479.

Success requires a non-empty, reproducible positive-advantage stratum and a
fresh paired simulator evaluation that does not regress candidate-only wins,
mean reward, or mean player HP. Failure closes this POC recipe without a seed,
horizon, threshold, or optimizer sweep.

## Capabilities

### New Capabilities

- `combat-rl-guard-advantage-residual`: Generate paired LightSTS action
  advantage evidence relative to the deployed guard baseline and train a
  development-only abstaining residual from that evidence.

### Modified Capabilities

None.

## Impact

The change affects only offline analysis scripts, focused tests, OpenSpec
artifacts, and report output. It may load the existing source-bound LightSTS
native module and simulator-only r16 shadow on CPU. It does not start the game,
load or write a production checkpoint, change live combat policy, qualify a
candidate, or authorize promotion. Rollback is deletion of the new POC script,
tests, and reports; production behavior remains untouched.
