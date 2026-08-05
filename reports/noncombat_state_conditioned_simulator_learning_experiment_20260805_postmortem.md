# State-Conditioned Simulator Learning Terminal Postmortem

## Decision

The single registered experiment is complete and terminal as
`experiment_stopped_at_canary`. An immediate successor experiment is `no_go`.
Formal non-combat RL, model loading, gameplay use, qualification, and promotion
remain `no_go`.

The state-conditioned model changed relative candidate scores and produced a
large floor shift against its frozen seeded initialization. It nevertheless
failed the preregistered behavior gate because every trained canary card-reward
decision selected `take`. The positive floor interval cannot override that
collapse, so the holdout remained untouched.

## Verified Execution

The authorized process exited with code 0 after 14,208.382 charged seconds. It
completed 4,096 training episodes, 64 optimizer updates, and 64 checkpoints.
The fresh-process standard-library verifier accepted all 75 listed artifacts,
all checkpoints, and the terminal classification.

Training observed only floor shaping:

| Episodes | Mean floor | Median | Max | >=17 | >=34 | >=51 | Victories | Unsupported |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4,096 | 14.142 | 16 | 50 | 695 | 13 | 0 | 0 | 41 |

The four training-pass mean effective floors were 13.543, 13.730, 14.147,
and 15.146. No training episode reached floor 51 or victory, so the optimizer
never observed the registered terminal-victory component.

## Canary Result

Both frozen policies completed all 128 canary seeds with exact replay and all
four target categories. Unsupported rows were retained conservatively at their
last supported floor; all four had the registered Courier restock reason.

| Policy | Mean floor | Median | Max | >=17 | >=34 | >=51 | Victories | Unsupported |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Frozen initialization | 13.398 | 14 | 33 | 17 | 0 | 0 | 0 | 1 |
| Frozen trained model | 24.148 | 24 | 50 | 89 | 5 | 0 | 0 | 3 |

The registered paired trained-minus-initial floor difference was +10.75 with
a 95% bootstrap interval of [8.9609375, 12.5390625]. Of 128 pairs, 104
improved, 14 were unchanged, and 10 declined. The combined unsupported rate
was 1.5625%, below the 10% ceiling, and victories were noninferior at 0 versus
0.

The anti-collapse gate still failed:

| Policy | Take | Skip | Bowl | Take rate |
| --- | ---: | ---: | ---: | ---: |
| Frozen initialization | 908 | 59 | 0 | 93.90% |
| Frozen trained model | 1,458 | 0 | 0 | 100.00% |

The trained policy had skip alternatives on 1,437 card-reward decisions and
never selected one. This is the exact registered blocker
`card_reward_selected_kind_saturation`. Shop did not collapse to one family:
the trained policy selected buy-card 419 times, potion 6, relic 1, leave 224,
and remove 13.

The successor did repair r2's deterministic state-cancellation defect. On
3,556 trained canary multi-candidate decisions, every recorded state
counterfactual changed relative scores and 366 changed candidate order. That
is useful architecture evidence, but it does not make the collapsed policy a
valid learning result or a quality baseline.

## Isolation And Holdout

`isolation.json` reports `unchanged=true`. CommunicationMod configuration and
the complete 1.356 GB production-checkpoint inventory match their pre-run
hashes. The game and CommunicationMod were not launched, no production model
was loaded or modified, and all downstream authority is false.

The canary stop occurred before holdout access. Holdout episode count is zero;
seeds `71152..71663` remain untouched and must not be inspected or reused to
tune this consumed experiment.

## Publication

The complete canonical terminal directory remains preserved locally. The raw
`training_rows.json` is 126,834,076 bytes, so ordinary Git stores a
deterministic 11,288,071-byte gzip archive instead. Its manifest binds both
hashes and the terminal artifact manifest. Restoring the raw file and running
the unchanged standalone verifier reproduces the full terminal bundle.

All other terminal artifacts are committed as their original canonical files.
The machine-readable postmortem binds the principal artifact hashes and exact
metrics in
`reports/noncombat_state_conditioned_simulator_learning_experiment_20260805_postmortem.json`.

## Next Gate

Do not propose another empirical run yet. The next work should be a source-only,
read-only audit over the existing training rows, checkpoints, model, and
canary diagnostics to determine when and why card-reward skip probability
collapsed. It should distinguish at least reward/credit assignment, action
representation, entropy strength, and optimizer trajectory without replaying a
seed, fitting a model, changing a threshold, or selecting a replacement
checkpoint.

Only a deterministic, evidence-backed mechanism and RED regression should
justify a new algorithm proposal. Any later experiment requires a fresh
identity, fresh cohort, immutable gates, and separate authorization. This
closeout does not establish policy quality, target-supported outcomes, formal
RL readiness, live value, or promotion eligibility.
