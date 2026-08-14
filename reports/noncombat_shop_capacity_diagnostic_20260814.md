# Shop Capacity Diagnostic

## Scope

- Source commit: `82c6768f36e7e2d1a7f4d5bf3079f4a2b6dcd80e`
- Historical sources: `112`, all unique across four completed shop cohorts
- Fold assignment: `shop-cross-validation-v1`, five source-level folds
- Models: existing candidate-only baseline, one fixed initialization per fold
- Epochs: `8`, `16`, `32`
- Native loading, fresh source access, gameplay, CommunicationMod, and protected seed access: `false`

Dataset SHA-256 bindings:

- train64: `e346d26e2e29d297b316d9247ef9cf6619bb3fce274b0b88f34d69a9be5f736a`
- development16: `c802f80ca72ea32f1caf42d1699faf92f607aac97af03b8b495f70ad9e07ba8e`
- robust16: `74a76101fabb6a61424f34a411d602e96be46f8f459ccc464b641ebb0c5e89a2`
- relative16: `76dde3cdcd058d6d9920f9795ddaf241915baa02f261776ab9b17bdbb49c4ae3`

## Results

| Policy | Mean regret | Maximum regret | Corrected | Worsened | Changed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Current | 0.203947 | 2.508772 | - | - | - |
| Candidate-only epoch 8 | 0.219612 | 2.508772 | 18 | 19 | 93 |
| Candidate-only epoch 16 | 0.215069 | 2.508772 | 19 | 16 | 93 |
| Candidate-only epoch 32 | 0.214756 | 2.315789 | 21 | 22 | 105 |
| Best state-conditioned ensemble OOF | 0.212719 | 2.614035 | 29 | 25 | 106 |

## Decision

Neither the low-capacity candidate-only baseline nor the state-conditioned ensemble improves Current mean regret on source-level OOF predictions. The shop path is data-limited at 112 sources; do not add another model or confidence-gate variant on this corpus. Preserve the unused fresh schedule and next expand independent simulator training support before another shop training attempt.
