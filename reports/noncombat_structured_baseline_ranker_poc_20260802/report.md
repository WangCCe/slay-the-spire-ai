# Non-Combat Structured Baseline-Ranker POC

- Verdict: `poc_valid_without_structured_candidate`
- Selected candidate: `None`
- Evidence class: `observed-train-only implementation fit`
- Policy-quality claim: `false`
- Registration SHA-256: `3a9aca0175bec6dddbeb17b96044c405c8e8e3b3486fc0f46f1c3ff3e126b49a`
- Train dataset SHA-256: `86cf82f7833ca6b7d3f4e58967f5768ef7292a2297d06af01819b783526227d0`

## Multi-Candidate Held-Out Metrics

| Metric | Legacy control | Structured | Delta |
| --- | ---: | ---: | ---: |
| Overall agreement | 0.700000 | 0.678161 | -0.021839 |
| Macro category agreement | 0.712301 | 0.633365 | -0.078936 |
| Mean cross entropy | 0.989680 | 1.182056 | +0.192376 |

## Category Agreement

| Category | Rows | Legacy | Structured | Delta |
| --- | ---: | ---: | ---: | ---: |
| card_reward | 302 | 0.668874 | 0.692053 | +0.023179 |
| event | 144 | 0.965278 | 0.798611 | -0.166667 |
| route | 300 | 0.666667 | 0.776667 | +0.110000 |
| shop | 124 | 0.548387 | 0.266129 | -0.282258 |

## Selection Checks

- card_reward_nonregression: `pass`
- cross_entropy_nonworse: `fail`
- macro_agreement_improvement: `fail`
- overall_agreement_improvement: `fail`
- replay_identity: `pass`
- route_nonregression: `pass`

## Data Strata

- Multi-candidate rows: 870
- Singleton rows excluded from fit/gate: 421
- Total train rows: 1291

## Structured Hash Diagnostics

- Hash width: 2048
- Unique feature keys: 825
- Occupied bins: 690
- Collision fraction: 0.163636

## Boundaries

- No validation or final-test row contributed to features, fitting, selection, or metrics.
- No native simulator, new seed, rollout, floor, victory, live game, checkpoint, or reward was used.
- SimpleAgent remains auxiliary supervision; all legal candidates remain available.
- A positive verdict authorizes only a separate fresh-study preregistration.

## Authority

- dagger: `false`
- formal_noncombat_rl: `false`
- live_gameplay: `false`
- live_policy_loading: `false`
- native_evidence_collection: `false`
- ope_reinterpretation: `false`
- policy_promotion: `false`
- qualification: `false`
- simulator_rollout: `false`
