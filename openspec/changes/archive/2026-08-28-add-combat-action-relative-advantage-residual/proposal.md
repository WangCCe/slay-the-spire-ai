## Why

The fixed post-guard multiclass residual failed its fresh LightSTS gate, and an
EndTurn safety mask removed most of that regression without beating guarded
control. The existing immutable corpus already contains 6,643 training and
3,439 evaluation alternatives with branch-relative returns, but the failed
objective trains only the single best action on positive rows and discards the
remaining action-value evidence.

## What Changes

- Add a development-only action-relative residual that scores each supported
  legal alternative against the guarded action from frozen parent features,
  candidate identity, guard identity, and the legal action context.
- Expand the existing corpus in memory into one supervised example per
  alternative and fit one fixed, source-bound regression/ranking recipe without
  collecting new gameplay data or sweeping hyperparameters.
- Preserve exact guard abstention, legal-action masking, and the registered
  post-guard EndTurn safety constraint during selection.
- Publish held-out action-value, ranking, calibration, selection, provenance,
  latency, and artifact-roundtrip evidence.
- If the fixed offline integrity conditions pass, run one preregistered fresh
  matched LightSTS comparison against guarded r16 and retain the recipe only if
  every control-relative policy condition passes.

Success requires a non-empty constrained intervention set, zero illegal or
forbidden actions, non-negative selected true advantage on the held-out corpus,
no nonterminal fresh-profile exclusions, candidate-only victories at least
control-only victories, and non-negative paired reward and player-HP deltas.

Non-goals are changing the frozen parent, guard, source corpus, branch-return
definition, production checkpoint, gameplay routing, CommunicationMod
configuration, or production policy. This change does not start the game; a
successful simulator result may justify a separately registered real-game
validation. Rollback removes the development scorer, runners, tests, and
bounded reports while leaving r16 and the archived failed residual unchanged.

## Capabilities

### New Capabilities

- `combat-rl-action-relative-advantage-residual`: Fit, serialize, select, and
  evaluate a post-guard action-relative advantage scorer from complete branch
  returns under fixed safety and authority boundaries.

### Modified Capabilities

None.

## Impact

The change affects a new `spirecomm.ai.rl.v2` development module, offline
training and evaluation runners, focused tests, OpenSpec artifacts, and bounded
reports. It reuses the immutable guard-advantage corpora, frozen simulator-only
r16 parent, and registered native LightSTS module on CPU. Production gameplay,
checkpoints, and CommunicationMod remain unchanged.
