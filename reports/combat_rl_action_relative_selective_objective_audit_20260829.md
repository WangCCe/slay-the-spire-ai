# Action-Relative Selective Objective Audit

## Decision

Replace scalar return regression and state-level gate/action decomposition with
one pair-level selective classifier. The next candidate should classify each
supported card or potion alternative relative to the actual guard action as
beneficial, neutral, or severe harm, rank actions by beneficial evidence, and
calibrate one fixed negative-class exclusion threshold before touching the
existing evaluation partition.

This audit is read-only. It did not fit a model, load native code, run
LightSTS, start gameplay, or change production r16.

## Existing candidate evidence

| Candidate | Holdout interventions | Precision | Mean selected advantage | Mean regret | Later evidence |
| --- | ---: | ---: | ---: | ---: | --- |
| Scalar action-relative residual | 162 | 0.383 | 0.123 | 3.247 | Matched live gate lost 0-2 with 8 ties |
| Five-member regression ensemble | 38 | 0.447 | 0.189 | 3.181 | Closed before fresh simulator |
| Family conformal margin | 0 | 0.000 | 0.000 | 3.452 | Card correction 7.136; potion correction 2.193 |

The earlier state-level `GuardAdvantageResidual` opened on 507 of 839 holdout
states. In its fresh paired LightSTS gate it intervened 2,969 times, produced 8
candidate-only victories versus 28 control-only victories, and reduced mean
reward by 1.748. Reusing that state gate with a different threshold would
repeat a closed recipe.

## Pair-label structure

The registered seed split leaves seeds `262000..262191` for fitting and
`262192..262255` for calibration. Evaluation seeds `263000..263127` remain
descriptive-only in this audit and SHALL remain unopened while defining or
fitting the next recipe.

Supported combat alternatives are card indices `0..59` and potion indices
`60..89`. EndTurn 90 is forbidden; indices `91..132` are noncombat reward,
map, event, shop, rest, and system actions and are absent from the LightSTS
combat bridge contract.

| Partition / family | Pairs | Beneficial `>=0.5` | Severe `<-0.5` | Neutral | Mean advantage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fit cards | 2,928 | 593 (20.3%) | 890 (30.4%) | 1,445 | -1.748 |
| Fit potions | 878 | 226 (25.7%) | 126 (14.4%) | 526 | 0.847 |
| Calibration cards | 959 | 206 (21.5%) | 301 (31.4%) | 452 | -1.454 |
| Calibration potions | 245 | 69 (28.2%) | 41 (16.7%) | 135 | 0.718 |

The fit partition contains 496 of 1,226 states (40.5%) with at least one
beneficial supported alternative. Calibration contains 164 of 407 (40.3%).
Coverage is therefore available; the hard problem is rejecting numerous
candidate-level false positives and choosing the right action within positive
states.

## Training implication

A three-class pair objective preserves information that prior recipes erased:

- beneficial: paired return advantage at least `0.5`;
- neutral: advantage from `-0.5` inclusive to `0.5` exclusive;
- severe harm: advantage below `-0.5`.

The model should consume frozen r16 latent state, guard identity, candidate
identity, and legal mask. It should train on fit rows only with deterministic
class-balanced pair batches plus an in-state ranking term. Calibration should
derive one predeclared threshold from non-beneficial scores and publish family
support and excluded rows. The untouched holdout then decides coverage,
precision, value, regret, severe harm, and legality once.

Do not tune thresholds, class boundaries, loss weights, update count, or action
families against the holdout. A holdout failure closes this recipe before any
fresh LightSTS or gameplay gate.
