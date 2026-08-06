# Hierarchical Simulator Learning Terminal Postmortem

## Decision

The single registered hierarchical experiment is complete and terminal as
`experiment_stopped_during_training_for_family_saturation`. An immediate
successor experiment is `no_go`. Formal non-combat RL, model loading, gameplay
use, qualification, and promotion remain `no_go`.

The hierarchical family-first objective did not repair the card-reward greedy
collapse seen in the consumed state-conditioned experiment. It kept stochastic
family probabilities close to balanced, but the raw-score ordering developed a
small, consistent, and growing `take` advantage. The registered four-chunk
gate therefore stopped training before canary or holdout access.

## Verified Execution

The authorized process exited with code 0 after 2,165.452 charged seconds. It
completed 512 training episodes, 8 optimizer updates, 8 checkpoints, and
11,807 policy decisions. It ran no evaluation episode.

The standalone standard-library verifier accepted all 22 listed artifacts, all
8 checkpoints, all 8 training chunks, the fixed Git and cohort identity, and
the terminal classification. The final verification reports
`repository_identity_verified=true`.

Training observed only floor shaping:

| Episodes | Mean floor | Median | Max | >=17 | >=34 | >=51 | Victories |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 512 | 12.629 | 13 | 44 | 41 | 1 | 0 | 0 |

These floor values are a read-only reconstruction from the recorded formal
`floor_progress` rows. The eight chunk mean floors were 11.797, 11.156,
12.250, 13.297, 12.141, 13.844, 12.906, and 13.641. No episode reached floor
51 or victory, so the optimizer never observed the terminal-victory reward.

## Family Saturation

Card-reward sampling remained diverse: across all chunks it selected `take`
1,790 times, `skip` 1,752 times, and `bowl` 17 times. That sampling diversity
did not translate into a valid greedy policy.

| Chunk | Greedy take / eligible | Mean take probability | Mean score margin | Mean family entropy |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 403 / 426 | 0.5041 | 0.0165 | 0.69310 |
| 1 | 383 / 389 | 0.5050 | 0.0201 | 0.69308 |
| 2 | 431 / 433 | 0.5078 | 0.0311 | 0.69301 |
| 3 | 463 / 464 | 0.5108 | 0.0430 | 0.69289 |
| 4 | 420 / 420 | 0.5134 | 0.0538 | 0.69276 |
| 5 | 472 / 472 | 0.5166 | 0.0663 | 0.69256 |
| 6 | 462 / 462 | 0.5200 | 0.0800 | 0.69230 |
| 7 | 493 / 493 | 0.5240 | 0.0959 | 0.69194 |

The terminal window was chunks 4 through 7. All 1,847 multi-family
card-reward decisions in that window had `take` as the unique raw-score maximum
family. Family entropy remained close to `ln(2)`, so this is not an
entropy-to-zero failure. It is a persistent sign and margin failure under the
registered raw-score greedy rule.

Shop did not trigger the gate. Its final four chunks contained 317
multi-family decisions with both `buy_card` and `leave` appearing as raw-score
maximum families, while stochastic selections covered all five shop families.

## Credit Signal

Within every chunk, card-reward decisions sampled as `take` had a higher mean
recorded normalized return than decisions sampled as `skip`. In the final
chunk those means were +0.190 for `take` and -0.089 for `skip`. This is
descriptive randomized-trajectory evidence, not a causal estimate: reward to
go, run health, decision timing, and repeated within-run choices remain
confounded.

The result narrows the next question. Splitting family and conditional entropy
was insufficient because near-uniform probabilities can still preserve one
greedy sign at every state. The next analysis must determine whether the
growing sign is driven by return attribution, state/opportunity imbalance,
or another recorded trajectory mechanism before proposing a different
baseline, advantage estimator, reward, coefficient, or architecture.

## Verifier Repair

The first post-exit verification correctly failed closed on a numeric mismatch.
The terminal artifacts were not changed. Diagnosis showed that the verifier's
sequential float32 summation did not reproduce the registered Torch CPU
reduction; policy loss differed by 5.7e-6 to 7.9e-6 across the eight chunks.

A five-value RED regression reproduced the discrepancy. The verifier now uses
`math.fsum` over float32-quantized inputs followed by one float32 cast. This
matches all eight recorded runtime losses within at most 6.1e-9 without
relaxing tolerance. The complete successor focused suites passed 92 tests, and
the pushed verifier-only repair `7319b762c` then accepted the unchanged
terminal bundle with full repository identity.

## Isolation And Cohorts

`isolation.json` reports `unchanged=true`. CommunicationMod configuration and
the complete 1.356 GB production-checkpoint inventory match their pre-run
hashes. The game and CommunicationMod were not launched, and no production
checkpoint was loaded or modified.

Canary and holdout episode counts are both zero. Registered canary seeds
`1122..1250` and holdout seeds `1251..1768` remain untouched. They stay bound
to this consumed identity and must not be inspected or reused to tune it.

## Publication

The complete canonical terminal bundle is preserved under
`reports/noncombat_hierarchical_simulator_learning_successor_20260806`. The
deterministic gzip training-row artifact binds 42,593,595 canonical bytes in a
4,174,910-byte file. Ordinary Git publication includes the full terminal
bundle and omits only the inactive `.execution.lease` control file.

The machine-readable postmortem binds the principal artifact hashes and exact
metrics in
`reports/noncombat_hierarchical_simulator_learning_successor_20260806_postmortem.json`.

## Next Gate

Do not start another empirical run. The next work should be a source-only,
read-only card-reward family credit-assignment audit over this experiment's
existing training rows and checkpoints. It should preregister descriptive
strata for decision timing, floor/run-health state, selection propensity,
reward to go, family margin, and checkpoint progression, and it must keep
causal and OPE claims false.

Only a deterministic mechanism supported by the consumed evidence and a RED
regression should justify a new algorithm proposal. Any later experiment needs
a fresh identity, fresh cohort, immutable gates, and separate authorization.
This closeout does not establish policy quality, target-supported outcomes,
formal RL readiness, live value, or promotion eligibility.
