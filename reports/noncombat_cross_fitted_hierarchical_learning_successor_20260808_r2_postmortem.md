# Cross-Fitted Hierarchical Learning r2 Terminal Postmortem

## Decision

The single authorized r2 execution is closed and independently valid as
`experiment_completed_with_cross_fitted_mechanism_evidence`. It completed all
eight registered chunks without a resume, failure, or family-saturation stop.
This is valid mechanism evidence, not policy-quality or formal-RL evidence.

An immediate successor experiment is `no_go`. The next gate is a read-only
audit of cross-fitted baseline support and card-reward advantage attribution
using only this sealed bundle. No canary, holdout, OPE, gameplay,
CommunicationMod, qualification, or promotion work is authorized by this
result.

## Verified Execution

The terminal bundle records 512 environment accesses, 8 optimizer updates, 8
checkpoints, 11,729 retained decisions, and 12,101.125 charged seconds. All
primary chunks `0..7` completed. The registered 64-access recovery reserve was
not used.

The standalone standard-library verifier rechecked the complete source,
native/runtime/isolation, journal, resource, baseline, advantage, gradient,
checkpoint, terminal, and manifest chains in 419 seconds. It accepted all 28
managed artifacts and returned the same verdict and resource counts. Terminal
SHA-256 is
`3de29ce568b0d418f4e1052c4b7c92040d2de316e035b455c47384daf48db1e0`.
Exact producer-canonical self-digest probes passed for terminal, terminal
intent, and manifest. The focused terminal/control/verifier gate passed 18
tests in 75.83 seconds.

| Evidence | Count |
| --- | ---: |
| Training trajectories | 512 |
| Retained decisions | 11,729 |
| Completed chunks | 8 |
| Optimizer updates | 8 |
| Checkpoints | 8 |
| Resumes | 0 |
| Victories observed | 0 |

## Cross-Fitted Mechanism

The cross-fitted baseline produced both positive and negative advantages:
6,326 positive, 5,396 negative, and 7 zero. Its per-chunk RMSE ranged from
0.1070 to 0.1861. The resulting policy gradient materially differed from the
legacy normalized-return gradient in every chunk:

| Metric across 8 chunks | Min | Mean | Max |
| --- | ---: | ---: | ---: |
| Gradient cosine vs legacy | 0.2866 | 0.5506 | 0.6616 |
| Cross-fitted gradient norm | 0.00253 | 0.00353 | 0.00467 |
| Legacy gradient norm | 0.02134 | 0.02565 | 0.02943 |

This establishes the registered mechanism claim: cross-fitted attribution is
not a cosmetic rewrite of the legacy update. It does not establish that the
new direction improves policy value.

Baseline support is an unresolved limitation. Of 11,729 predictions, 2,261
(19.3%) were below zero and clipped to the registered lower bound; none hit the
upper bound. Low clipping occurred in 1,232 route, 659 card-reward, 200 shop,
and 170 event decisions. The unclipped prediction range was -0.3582 to 0.8429.

## Card-Reward Near Saturation

Stochastic family sampling remained diverse across 3,536 card-reward
decisions: `take` 1,836, `skip` 1,672, and `bowl` 28. Greedy raw-score behavior
did not become meaningfully diverse: `take` was the maximum family in 3,512
decisions, `skip` in 22, and `bowl` in 2.

In the registered final four-chunk window, `take` was greedy for 1,773 of
1,774 multi-family decisions. One `bowl` maximum prevented the exact all-one-
family saturation predicate from firing, so the run correctly completed under
the preregistered rule. Operational completion must not be interpreted as a
repair of card-reward collapse.

Mean cross-fitted advantage by sampled card-reward family was +0.00954 for
`take`, +0.00278 for `skip`, and +0.05591 for the sparse 28 `bowl` samples.
These are descriptive trajectory-conditioned values, not causal effects.

Shop was less concentrated. Across all chunks its greedy family was
`buy_card` 641 times, `leave` 237, `buy_potion` 7, and `buy_relic` once.
Stochastic selections covered all five registered shop families.

## Outcomes And Isolation

The 512 training trajectories observed no victory. Initial trajectory returns
ranged from 0.01754 to 0.57895 with mean 0.21913. No evaluation cohort was
registered or accessed, so the evidence cannot compare the fitted policy with
Current, Bottled, SimpleAgent, or another checkpoint.

Both isolation observations match registration. The CommunicationMod config
and all 208 production checkpoint files totaling 1,356,047,034 bytes are
unchanged. Slay the Spire and CommunicationMod were not launched, and no
production checkpoint was loaded or modified.

## Monitoring And Publication

The long-running shell wait handle was lost during a conversation-context
transition, so the wrapper exit code is unavailable. A true-process query
confirmed that the registered Python child had exited before any output-root
artifact was read. No second execution, resume, signal, or active-root read was
performed. The independently valid terminal bundle supplies the authoritative
completion evidence.

The complete canonical bundle is preserved under
`reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2`.
Its manifest binds 28 managed artifacts, 91,187,429 stored bytes, and
243,933,540 uncompressed bytes. Ordinary Git publication omits only the
inactive `.execution.lease` control file.

No implementation or test source changed. The known long commit gate and
fresh gameplay validation are therefore not applicable to this evidence-only
closeout and were not run.

## Next Gate

Do not start an immediate successor experiment. First run a source-only,
read-only audit over these existing chunks that:

- stratifies baseline clipping and residuals by fold, chunk, category, state,
  and selected family;
- decomposes card-reward family-policy gradients by clipped/unclipped support,
  advantage sign, selected family, and checkpoint progression; and
- explains the final-window 1,773/1 near-saturation pattern without changing
  the registered saturation predicate or treating the single `bowl` row as
  evidence of robust diversity.

Only a deterministic mechanism and RED regression from that audit should
justify a new algorithm proposal. This closeout grants no policy-quality,
causal, formal-RL, target-supported-outcome, live-value, qualification, or
promotion claim.
