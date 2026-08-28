## Why

The fixed post-guard residual regressed on fresh LightSTS outcomes, and the
strongest mechanism-level cluster reverses the guard back to `EndTurn`: 261
such interventions occurred in 191 paired profiles with 3 candidate-only wins
versus 19 control-only wins, mean reward delta -8.02, and mean HP delta -6.76.
The source corpus also labels `EndTurn` as the positive target in 14.44% of
training positives, so this is a repeated objective/safety conflict rather than
an isolated action.

## What Changes

- Add a post-guard residual action constraint that always excludes `EndTurn`
  from residual alternatives after the wasteful-EndTurn guard has fired.
- Keep the frozen parent, guard, residual artifact, gate threshold, and model
  parameters unchanged; perform no fitting or tuning.
- Run one preregistered, fresh three-arm matched LightSTS ablation: guarded
  control, unrestricted residual, and EndTurn-masked residual.
- Require the masked arm to produce zero residual EndTurn interventions,
  improve over the unrestricted arm on the same cohort, and independently pass
  every existing control-relative simulator policy condition.
- Close the safety hypothesis without another action filter, threshold change,
  seed change, or training run if any fixed condition fails.

The success metric is a masked arm that passes the existing candidate-only
victory, reward, HP, nonterminal-support, and intervention conditions while
also eliminating residual EndTurn interventions and improving reward and HP
relative to the unrestricted residual on the same profiles.

Non-goals are retraining the residual, changing its threshold or architecture,
changing the guard, starting Slay the Spire or CommunicationMod, loading a
production checkpoint, or authorizing gameplay, qualification, or promotion.
Rollback removes the offline action constraint, runner, tests, and reports;
production r16 remains unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-rl-guard-advantage-residual`: Require a fixed action-safety boundary
  and fresh three-arm causal ablation before retaining a residual that can
  otherwise reverse a wasteful-EndTurn guard intervention.

## Impact

The change affects only the offline residual evaluation path, focused tests,
OpenSpec artifacts, and bounded reports. It reuses the immutable native module,
simulator-only r16 shadow, and development-only residual artifact on CPU. It
does not change gameplay routing, CommunicationMod configuration, production
checkpoints, or production policy behavior.
