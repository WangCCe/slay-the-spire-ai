# Hierarchical Card-Reward Credit-Assignment Audit

## Verdict

`direct_take_pressure_aligned_but_stratum_heterogeneous`

This verdict is descriptive only. It does not authorize an algorithm change or another empirical run.

## Evidence

- Training chunks: 8
- Training episodes: 512
- Aligned decisions: 11807
- Eligible card rewards: 3559
- Recorded take selections: 1790
- Recorded skip selections: 1752
- Global support: supported
- Terminal-window mean margins: 0.053769436, 0.066254920, 0.079994048, 0.095918210

## Chunk Pressure

| Chunk | Eligible | Take | Skip | Combined pressure | Mean margin |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 426 | 212 | 210 | 0.00306849557033 | 0.016504045 |
| 1 | 389 | 187 | 202 | 0.0213633503107 | 0.020127770 |
| 2 | 433 | 224 | 206 | 0.00603740594611 | 0.031080624 |
| 3 | 464 | 231 | 232 | 0.00840240629028 | 0.043041175 |
| 4 | 420 | 212 | 207 | 0.0110089316874 | 0.053769436 |
| 5 | 472 | 237 | 233 | 0.0102278908291 | 0.066254920 |
| 6 | 462 | 244 | 212 | 0.0112505637604 | 0.079994048 |
| 7 | 493 | 243 | 250 | 0.0218355281939 | 0.095918210 |

## Limitations

- Direct family-logit pressure is a factorized coordinate derivative, not the full shared-parameter gradient.
- Recorded reward-to-go associations are trajectory-confounded and are not causal card values or intervention effects.
- Repeated decisions within a seed are not treated as independent samples.
- The audit estimates no policy value, OPE quantity, confidence interval, p-value, or target-supported outcome.
- No verdict authorizes training, replay, seed access, model loading, gameplay, qualification, or promotion.

## Authority

- causal_claim_authorized: false
- cohort_materialization_authorized: false
- communication_mod_authorized: false
- environment_construction_authorized: false
- execution_authorized: false
- formal_rl_authorized: false
- fresh_evidence_authorized: false
- gameplay_authorized: false
- live_execution_authorized: false
- model_fitting_authorized: false
- native_loading_authorized: false
- ope_authorized: false
- policy_loading_authorized: false
- production_checkpoint_mutation_authorized: false
- promotion_authorized: false
- qualification_authorized: false
- seed_access_authorized: false
- target_supported_outcome_authorized: false
- training_authorized: false
