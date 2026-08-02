# Route/Card Residual-Ranker POC Failure Audit

## Conclusion

The terminal train-only residual POC is a deterministic valid negative. The
candidate MUST NOT advance to fresh simulator evidence: overall held-out
multi-candidate agreement improved by only `0.11` percentage points, macro
agreement by `0.08` points, and overall cross entropy by `0.0009`. Card-reward
agreement did not change, route agreement improved by only `0.33` points, and
fold 1 regressed on route agreement.

The experiment nevertheless validates its engineering hypothesis boundaries.
The frozen legacy base remained byte-identical, event/shop delegated exactly on
all 268 held-out rows, residual corrections stayed within the registered bound,
and primary/replay execution identities matched. No model was selected and all
downstream authority remains false.

## Bound Evidence

- Registration SHA-256:
  `eaf3e5f493d1686ca2cbff87571eee5ed1fa375c5e364a7d7d9cf7c568677676`
- Train dataset SHA-256:
  `86cf82f7833ca6b7d3f4e58967f5768ef7292a2297d06af01819b783526227d0`
- Primary/replay execution SHA-256:
  `6c6c4498e94925457c1870fce921150bcc46e6bf4cc2d3f1ae6dbdd57df1e108`
- Metrics SHA-256:
  `998e554f0ff6307ebbb408c4c59ecc4df7e6324a8f2f91e60e416aabe776046d`
- Predictions SHA-256:
  `3fc5f51912db649a1dcecb0576bff69911fa2ec012a103595b9d41c99e1f35cb`
- Rows: 1,291 total, 870 multi-candidate, 421 singleton excluded from
  fitting and competence gates.
- Execution time: 115.25 seconds primary and 111.922 seconds replay, each
  below the registered 900-second bound.

The published eight-file inventory contains seven hash-closed canonical files
plus one noncanonical timing journal. The standalone validator rehashed and
semantically reconstructed probabilities, base-plus-residual scores, aggregate
and per-fold metrics, delegation, residual diagnostics, gate classification,
selected-model absence, authority, and inventory successfully.

## Terminal Gate

| Check | Observed | Required | Result |
| --- | ---: | ---: | --- |
| Overall agreement delta | +0.001149 | >= +0.030000 | fail |
| Macro agreement delta | +0.000833 | >= +0.020000 | fail |
| Card agreement delta | +0.000000 | >= +0.010000 | fail |
| Card cross-entropy delta | -0.001006 | <= -0.010000 | fail |
| Route agreement delta | +0.003333 | >= +0.050000 | fail |
| Route cross-entropy delta | -0.001516 | <= -0.010000 | fail |
| Every-fold non-regression | 3/4 folds | 4/4 folds | fail |
| Event/shop exact delegation | 268/268 rows | all rows | pass |
| Frozen base immutability | 4/4 folds | all folds | pass |
| Replay identity | exact | exact | pass |

Cross entropy improved slightly in both learned categories and in every fold,
but not by a decision-relevant margin. Fold 1 lost one correct route choice,
producing route agreement delta `-0.016129` and macro agreement delta
`-0.004032`; this independently fails the fold-stability boundary.

## Error Shape

| Category | Both correct | Legacy only | Residual only | Both wrong | Action flips |
| --- | ---: | ---: | ---: | ---: | ---: |
| card_reward | 202 | 0 | 0 | 100 | 0 |
| event | 139 | 0 | 0 | 5 | 0 |
| route | 199 | 1 | 2 | 98 | 3 |
| shop | 68 | 0 | 0 | 56 | 0 |

Only three of 870 held-out actions changed, all on route rows:

- Seed 4004, fold 0: corrected `route:map_node:3:14` to target
  `route:map_node:1:14`.
- Seed 4025, fold 1: changed the correct `route:map_node:4:0` to incorrect
  `route:map_node:0:0`.
- Seed 4027, fold 3: corrected `route:map_node:0:8` to target
  `route:map_node:1:8`.

The residual produced no card-reward action change. Its maximum absolute
correction was `0.011595`, mean absolute correction `0.002253`, and RMS
`0.002917` against a registered bound of `1.0`. Per fold, residual training
loss decreased by only about `0.0011` across 20 epochs. The candidate therefore
stayed very close to the legacy logits: this protected event/shop and
calibration, but did not recover the standalone structured route signal.

This observation does not authorize a higher learning rate, more epochs,
larger residual scale, alternate loss, or third model trial. Those changes
would be post-result tuning on the same already observed corpus, explicitly
forbidden by the registration.

## Integrity And Authority

- The same trained legacy base supplied control and candidate logits in each
  fold and remained immutable before/after residual fitting and evaluation.
- All 32 seeds remained grouped in four deterministic held-out folds; every
  multi-candidate decision appears exactly once in each policy's predictions.
- Candidate ids, logits, probabilities, selected actions, and target
  probabilities matched exactly between control and residual for event/shop.
- The residual used only route/card structured features; no validation/final
  row, native state, new seed, outcome, reward, prior prediction, or prior
  metric entered fitting or selection.
- `models.json` contains four base/residual fold identities and training
  histories. Selected model, selected-model hash, and replay selected-model
  hash are null.
- Native collection, simulator rollout, live gameplay/loading, DAgger, formal
  RL, OPE reinterpretation, qualification, policy quality, and promotion
  authority are all false.

## Next Gate

Stop baseline-imitation model experiments on this corpus. Do not preregister a
fresh policy-quality study and do not start formal non-combat RL.

The next change should be a read-only state/action sufficiency and teacher
suitability audit. Without fitting another model or loading the native module,
it should:

1. Trace the local `sts_lightspeed` SimpleAgent route/card decision code and
   enumerate every input it reads.
2. Compare those dependencies with the adapter snapshot, candidate schema, and
   legacy/structured projections to identify omitted, conflated, or unstable
   semantics.
3. Quantify observable-state aliasing and conflicting SimpleAgent labels in the
   preserved train corpus, with exact and explicitly bounded approximate keys.
4. Separate representation insufficiency from teacher-policy limitations and
   issue a go/no-go among adapter representation repair, a different auxiliary
   target, or abandoning supervised imitation as the policy-quality gate.
5. Require a separate OpenSpec before any adapter change, new evidence, model
   fit, DAgger, or formal RL work.
