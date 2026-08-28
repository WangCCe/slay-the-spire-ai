# Combat RL LightSTS guard transfer POC

- Verdict: `lightspeed_guard_pretraining_confirmed_on_independent_replay`
- Simulator transitions: `12417`
- Real decision spans: `852`
- No policy candidate or production artifact was created.

| Arm | ROC AUC | Direct open | Changed open | Open precision |
|---|---:|---:|---:|---:|
| `legacy_real_only` | 0.7973 | 0.1400 | 0.6454 | 0.8686 |
| `latent_real_only` | 0.8468 | 0.1629 | 0.7311 | 0.8656 |
| `latent_sim_pretrained` | 0.8697 | 0.1400 | 0.7590 | 0.8860 |

## Independent replay holdout

| Arm | ROC AUC | Direct open | Changed open | Open precision |
|---|---:|---:|---:|---:|
| `legacy_real_only` | 0.8280 | 0.1935 | 0.6839 | 0.8944 |
| `latent_real_only` | 0.8471 | 0.1774 | 0.7466 | 0.9098 |
| `latent_sim_pretrained` | 0.8868 | 0.1398 | 0.8341 | 0.9347 |

This is development-only evidence from an already-used real replay corpus.
It does not authorize gameplay, qualification, or promotion.
