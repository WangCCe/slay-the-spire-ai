# Combat RL LightSTS guard transfer POC

- Verdict: `latent_gated_correction_supported_on_independent_replay`
- Simulator transitions: `12762`
- Real decision spans: `852`
- No policy candidate or production artifact was created.

| Arm | ROC AUC | Direct open | Changed open | Open precision |
|---|---:|---:|---:|---:|
| `legacy_real_only` | 0.7973 | 0.1400 | 0.6454 | 0.8686 |
| `latent_real_only` | 0.8468 | 0.1629 | 0.7311 | 0.8656 |
| `latent_sim_pretrained` | 0.8705 | 0.1486 | 0.7530 | 0.8791 |

## Independent replay holdout

| Arm | ROC AUC | Direct open | Changed open | Open precision |
|---|---:|---:|---:|---:|
| `legacy_real_only` | 0.8280 | 0.1935 | 0.6839 | 0.8944 |
| `latent_real_only` | 0.8471 | 0.1774 | 0.7466 | 0.9098 |
| `latent_sim_pretrained` | 0.8873 | 0.1398 | 0.8498 | 0.9358 |

## Latent-gated action correction

- Verdict: `latent_gated_action_correction_supported`
- Overall agreement: parent `0.2943`, candidate `0.5000`
- Direct agreement: `0.9570`
- Changed agreement: `0.3094`
- Changed raw correction agreement: `0.4013`
- Positive-energy end-turn delta: `-321`

This is development-only evidence from an already-used real replay corpus.
It does not authorize gameplay, qualification, or promotion.
