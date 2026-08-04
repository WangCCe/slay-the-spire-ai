# Non-Combat Simulator RL r2 Terminal Postmortem

## Decision

An immediate r3 experiment is `no_go`. Formal non-combat RL, model loading,
gameplay use, and promotion remain `no_go`.

r2 provides valid evidence that the trained greedy ranker advances farther than
its seeded CandidateRanker initialization. It does not provide victory learning,
a credible non-combat baseline comparison, or a state-conditioned policy:

- all 4,096 training episodes, 256 canary policy episodes, and 1,024 holdout
  policy episodes produced zero victories;
- no observed policy episode reached floor 51;
- every trained canary and holdout card-reward action was `take`; and
- the registered linear architecture cancels all shared state-only features
  from relative candidate scores.

Any successor must first repair and regress the state/action interaction. It
must not reuse this cohort or treat the r2 floor shift as promotion evidence.

## Scope And Inputs

This is a read-only descriptive audit of the closed r2 artifacts. It did not
load Torch or the native simulator, access a new seed, replay an episode, fit a
model, bootstrap a new interval, or define a new qualification threshold.

For unsupported rows, `effective_floor` is the registered disposition:
`terminal_floor` when present, otherwise `last_supported_floor`. Raw missing
terminal-floor counts remain reported separately. Quantiles use linear
interpolation at `(n - 1) * probability`.

The machine-readable report binds every input and source file by SHA-256:
`reports/noncombat_simulator_rl_experiment_20260804_r2_postmortem.json`.
The principal bindings are:

| Artifact | SHA-256 |
| --- | --- |
| Registration | `8e0576bbf86b2334ccce67ac809410a02dcbfa6419f075211bbe48d0164f8549` |
| r2 manifest | `ae208ee1e34d34495cb5bc76dc6bc73431d904b9a889f1c8267a1eaf25d6d4a7` |
| Evaluation | `50b30261bc722e24383c59bd7c7be2ae959c47b12e5cb22f2e4ee5dbdd721886` |
| Metrics | `ad25f81342f782f8238584ee8923f330a9399f9a43b95dc12cf6455d7df10b9a` |
| Final model | `28a638514d5a91aa04020b9bc740708685834f9655a0785bba2e48229098b397` |

## Floor Evidence

| Cohort / policy | Episodes | Mean | Median | Max | >=17 | >=34 | >=51 | Victories | Unsupported |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Training executions | 4,096 | 13.608 | 14 | 50 | 552 | 9 | 0 | 0 | 23 |
| Canary initial | 128 | 11.750 | 11 | 46 | 9 | 1 | 0 | 0 | 2 |
| Canary trained | 128 | 22.102 | 20 | 46 | 70 | 7 | 0 | 0 | 4 |
| Holdout initial | 512 | 11.791 | 12 | 33 | 21 | 0 | 0 | 0 | 4 |
| Holdout trained | 512 | 22.322 | 21 | 50 | 278 | 30 | 0 | 0 | 11 |

The registered paired results are confirmed:

| Cohort | Mean difference | Registered 95% CI | Improved / same / declined | Both-supported mean |
| --- | ---: | --- | --- | ---: |
| Canary | +10.3516 | [8.5391, 12.1563] | 98 / 23 / 7 | +10.5968 (124 pairs) |
| Holdout | +10.5313 | [9.6855, 11.3984] | 408 / 82 / 22 | +10.7680 (500 pairs) |

The floor shift is broad, not an unsupported-row artifact. In holdout, 403 of
500 both-supported pairs improved, while 501 of 512 trained episodes were
supported non-victories. However, neither policy crossed floor 51 and the
trained maximum was 50, so the result contains no terminal-victory evidence.

Training-pass means were 13.452, 13.535, 13.772, and 13.671. Mean chunk loss
declined from 0.03649 to 0.02786, but stochastic rollout floor means did not
improve monotonically. All 4,096 scalar rewards exactly match the registered
contract, and the `+2` victory component was observed zero times. The optimizer
therefore received floor-progress returns only.

## Decision Behavior

| Cohort / policy | Card take | Card skip | Bowl | Take rate |
| --- | ---: | ---: | ---: | ---: |
| Canary initial | 325 | 444 | 0 | 42.26% |
| Canary trained | 1,384 | 0 | 0 | 100.00% |
| Holdout initial | 1,308 | 1,725 | 2 | 43.10% |
| Holdout trained | 5,542 | 0 | 0 | 100.00% |

Raw action totals differ because the trained policy reaches more decisions, so
the within-category rates are the relevant comparison. The zero trained skips
are not caused by differing first states: all 128 canary pairs and all 512
holdout pairs have matching policy-input hashes at their first action mismatch.
In holdout, first divergence was card reward for 363 pairs, route for 139,
event for 6, and shop for 4. Of the card-reward divergences, 272 changed from
initial `skip` to trained `take` and 91 selected a different `take` action.

This is a material action-family saturation signal. It is compatible with the
floor improvement, but it is not evidence of robust card-reward strategy.

## Structural Blocker

The registered implementation uses a one-output linear `CandidateRanker` and
constructs each candidate row as:

```text
features_i = shared_state_features + candidate_features_i
score_i = weight dot features_i + bias
```

For candidates `i` and `j` in the same decision:

```text
score_i - score_j = weight dot (candidate_features_i - candidate_features_j)
```

The shared state term and bias cancel exactly. State-only features therefore
cannot affect softmax probabilities or greedy ordering. Candidate-local fields
can still carry context such as legality or price, but the separately encoded
deck, resources, floor, and decision state cannot condition relative ranking
unless that context is duplicated into each candidate.

The relevant files are unchanged from the registered implementation commit
`8d123fdf32bd94bc29e53a97f217a2b7ca40c4fe`:

- `analysis_scripts/noncombat_policy_model.py` defines the linear scorer.
- `analysis_scripts/noncombat_simulator_rl_experiment.py` adds the shared state
  vector to every candidate vector before scoring.

This is a deterministic capacity blocker, not a post-hoc statistical claim.
It prevents r2 from establishing meaningful state-conditioned non-combat RL.

## Data Quality

Across 5,376 training and evaluation policy episodes, 44 (0.8185%) were
unsupported. All 44 have the registered reason
`unsupported_shop_courier_restock_semantics`; their missing `terminal_floor`
values exactly match unsupported status, and all retain a finite
`last_supported_floor`. The known simulator gap is low-rate and correctly
accounted for. It does not explain zero victories or the card-reward saturation.

Python structured recomputation with invariant assertions and an independent
PowerShell `ConvertFrom-Json` implementation agreed on the bound hashes, row
counts, effective-floor summaries, thresholds, action-family counts, paired
directions, first-divergence input identity, and unsupported accounting.

## Next Gate

The next change should be an OpenSpec proposal for state-conditioned candidate
ranking and anti-collapse diagnostics. Before any fresh experiment it should:

1. Introduce an interaction-capable scorer or explicit state/action interaction
   features while preserving deterministic CPU execution and legal masks.
2. Add a regression where changing only decision state can reverse the ordering
   of an unchanged candidate set, plus a deterministic repeat regression.
3. Report per-category candidate availability, selected action-family rates,
   score margins, and skip/take saturation in canary and holdout.
4. Define a meaningful fixed non-combat comparator instead of treating seeded
   random initialization as policy-quality evidence.
5. Require a fresh identity, fresh cohort decision, and separate authorization
   before simulator execution.

The existing formal-readiness blockers remain
`credible_baseline_floor_not_demonstrated` and
`target_supported_outcome_evidence_not_demonstrated`. This postmortem grants no
new experiment, cohort, training, replay, model-loading, gameplay, formal-RL,
qualification, or promotion authority.
