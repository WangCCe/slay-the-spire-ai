# Non-Combat Simulator Baseline Warm Start

## Status

The implementation-fit evidence and the one registered study are complete.
Implementation fit reused only the already observed adapter fit seeds `0..19`.
The study used train seeds `4000..4031` and validation seeds `5000..5015`, then
stopped at the preregistered validation gate. Final-test seeds `6000..6031`
remain untouched.

The study remains a bounded supervised warm-start experiment. Native
SimpleAgent actions are auxiliary demonstrations, not reward, permanent truth,
or a policy-promotion target. Current and Bottled remain excluded until their
simulator feature/action bridges are separately validated.

## Registered Study Result

The primary execution and identical replay matched canonically. Their bounded
execution times were 428.27 and 431.49 seconds. Training collected 1,291 rows;
validation collected 705 rows; no final-test dataset or trajectory exists.

| Validation metric | Result | Gate |
| --- | ---: | ---: |
| Overall exact teacher action agreement | 0.790071 | at least 0.80 |
| Macro-category exact agreement | 0.786065 | at least 0.75 |
| Minimum per-category agreement | 0.640000 | at least 0.60 |
| Candidate-minus-SimpleAgent mean floor | -4.687500 | at least -1.0 |
| Paired 95% interval lower bound | -11.689062 | at least -3.0 |

Per-category teacher agreement was 0.640000 for card reward, 0.927536 for
event, 0.845953 for route, and 0.730769 for shop. On 16 paired validation
seeds, the candidate averaged floor 20.0 and native SimpleAgent averaged
24.6875; each policy recorded one victory. The teacher macro and per-category
checks passed, while overall agreement, mean floor deficit, and lower-bound
non-inferiority failed.

The verdict is `study_valid_without_baseline_floor`. This is a valid negative
result, not a blocked execution. It does not authorize formal RL or another
training run. The next stage is read-only attribution of the existing
validation divergences before proposing a different warm-start/data-aggregation
method.

The complete canonical corpus remains in the local result directory. Because
its raw JSON is 320,965,025 bytes, the repository publishes a deterministic
13,416,133-byte gzip copy and a raw/compressed hash manifest under
`reports/noncombat_simulator_baseline_warm_start_20260802_archive/`. Restoring
the raw file reproduces the SHA-256 bound by the canonical artifact manifest.

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
