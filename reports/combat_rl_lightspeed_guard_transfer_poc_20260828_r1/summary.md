# Combat RL LightSTS guard transfer POC

- Verdict: `parent_latent_helps_but_lightspeed_transfer_is_not_proven`
- Simulator transitions: `12421`
- Real decision spans: `852`
- No policy candidate or production artifact was created.

| Arm | ROC AUC | Direct open | Changed open | Open precision |
|---|---:|---:|---:|---:|
| `legacy_real_only` | 0.7973 | 0.1400 | 0.6454 | 0.8686 |
| `latent_real_only` | 0.8468 | 0.1629 | 0.7311 | 0.8656 |
| `latent_sim_pretrained` | 0.8747 | 0.1686 | 0.7689 | 0.8674 |

This is development-only evidence from an already-used real replay corpus.
It does not authorize gameplay, qualification, or promotion.
