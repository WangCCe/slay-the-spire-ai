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
| `legacy_real_only` | 0.8302 | 0.0925 | 0.5184 | 0.8704 |
| `latent_real_only` | 0.8578 | 0.1233 | 0.6471 | 0.8627 |
| `latent_sim_pretrained` | 0.9012 | 0.1674 | 0.8382 | 0.8571 |

## Latent-gated action correction

- Verdict: `latent_gated_action_correction_supported`
- Overall agreement: parent `0.4549`, candidate `0.5942`
- Direct agreement: `0.9405`
- Changed agreement: `0.3051`
- Changed raw correction agreement: `0.3989`
- Positive-energy end-turn delta: `-415`

This is development-only evidence from an already-used real replay corpus.
It does not authorize gameplay, qualification, or promotion.
