# Non-Combat Simulator Baseline Warm Start

## Status

The implementation-fit evidence is complete. It reused only the already
observed adapter fit seeds `0..19`, made no policy-quality claim, and granted no
training or live authority. No native environment has been constructed for the
fresh study cohorts below.

The study remains a bounded supervised warm-start experiment. Native
SimpleAgent actions are auxiliary demonstrations, not reward, permanent truth,
or a policy-promotion target. Current and Bottled remain excluded until their
simulator feature/action bridges are separately validated.

## Committed Implementation-Fit Evidence

The committed implementation-fit report contains 770 demonstration rows over
20 episodes:

| Category | Rows | Rows per seed |
| --- | ---: | ---: |
| card_reward | 195 | 9.75 |
| event | 91 | 4.55 |
| route | 407 | 20.35 |
| shop | 77 | 3.85 |

Two collections were byte-identical. Two fixed 10-epoch training executions
produced identical initial models, final models, and histories. Mean collection
time was 59.66 seconds per 20 seeds and mean training time was 53.78 seconds per
770 rows on the registered machine. These measurements establish implementation
fit and bounded-cost estimates only; they contain no teacher-fit or candidate
rollout quality result.

## Preregistered Study Values

### Cohorts

| Cohort | Seeds | Count | Expected rows from fit density |
| --- | --- | ---: | ---: |
| train | `4000..4031` | 32 | about 1,232 |
| validation | `5000..5015` | 16 | about 616 |
| final_test | `6000..6031` | 32 | about 1,232 |

The cohorts are mutually disjoint and exclude every prior adapter fit, smoke,
compatibility, and policy-validity seed. Pure fake-environment tests that use
similar integers do not constitute native seed observation.

### Fixed Model And Optimizer

- Architecture: `candidate-ranker-mlp-v1`
- Features: `noncombat-simulator-policy-features-v1`
- Dimensions: 1024 input, 128 ReLU hidden units, one candidate score
- Initialization: CPU, model seed 0, no dropout
- Objective: category-balanced candidate-masked cross entropy
- Optimizer: Adam, 10 epochs, learning rate 0.001, betas 0.9/0.999,
  epsilon `1e-8`, zero weight decay
- Model configurations, parameter retries, and alternate cohorts: exactly one,
  all substitutions disabled

### Quality Gates

| Metric | Threshold |
| --- | ---: |
| Overall exact teacher action agreement | at least 0.80 |
| Macro-category exact agreement | at least 0.75 |
| Per-category exact agreement | at least 0.60 |
| Candidate-minus-SimpleAgent floor CI lower bound | at least -3.0 |
| Candidate-minus-SimpleAgent mean floor difference | at least -1.0 |

The teacher thresholds require broad representation fit without treating
SimpleAgent as optimal. The rollout gate remains primary. A three-floor lower
confidence margin permits seed variance, while the one-floor mean-deficit limit
prevents a broad but systematically weaker policy from passing. Both validation
and final test use the same fixed values. The paired interval uses 5,000
deterministic bootstrap resamples, seed 0, and 95% confidence.

### Resource Bounds

- Maximum 500 decisions per episode and 10,000 demonstration rows
- Maximum 32 train episodes, 32 validation policy episodes, and 64 final policy
  episodes
- Maximum 128 policy episodes and 10 optimizer epochs per execution
- Maximum 720 seconds per primary execution or replay
- Exactly one primary execution and one identical replay

The 720-second limit is conservative relative to the measured collection and
training costs and leaves room for candidate-policy feature projection. It is a
hard stop, not a target duration.

## Stop And Authority Contract

Validation is a stop gate. If any validation structural or quality threshold
fails, final-test seeds remain untouched and no alternate model, threshold,
cohort, or retry is allowed. A passing final result authorizes only consideration
of a separate formal-RL proposal. Formal RL, simulator RL training, live
gameplay, live loading, live study launch, OPE reinterpretation, qualification,
and promotion all remain false under this change.
